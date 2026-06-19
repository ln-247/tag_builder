import pandas as pd
import numpy as np
from pathlib import Path # для определения расширения файла - путь файла

import json
import sqlite3
import tempfile

#TAG BUILDER

def read_file(taglist_file):
    file_type = Path(taglist_file.name).suffix.lower()
    if file_type == ".csv":
        tags_table = pd.read_csv(taglist_file)
    elif file_type in [".xlsx", ".xls"]:
        tags_table = pd.read_excel(taglist_file)
    elif file_type == ".ods":
        tags_table = pd.read_excel(taglist_file, engine="odf")
    else:
        raise ValueError(f"Неподдерживаемый тип файла: {file_type}")
    return tags_table

def normalize_tags_table(tags_table):
    columns = ["scale_min","scale_max","lolo","lo","hi","hihi"]
    for colmn in columns: # заменить запятую на точку в числовых значениях
        tags_table[colmn] = tags_table[colmn].astype(str).str.replace(",", ".", regex=False)
        tags_table[colmn] = pd.to_numeric(tags_table[colmn], errors="coerce")#для случаев с нан или -
    
    tags_table = tags_table.astype({'name':'object','desc':'object','unit':'object',
                                    'scale_min':'float64','scale_max':'float64','dec':'Int64','lo':'float64','lolo':'float64',
                                    'hi':'float64','hihi':'float64', 'type':'object'}) #cnfylfhnbpbhjdfnm типы столбцов
    
    columns_template = ['name','tag_type','initial_value','desc','unit','scale_min','scale_max',
            'dec','access_type','group_name','logged','lo','lolo','hi','hihi','discrete_alarm_value'] #стандартные имена и порядок столбцов
    table_result = tags_table.reindex(columns=columns_template + [c for c in tags_table.columns if c not in columns_template])

    table_result = table_result.astype({'name':'object','tag_type':'Int64','initial_value':'Int64','desc':'object','unit':'object',
                                    'scale_min':'float64','scale_max':'float64','dec':'Int64','access_type':'Int64',
                                    'group_name':'Int64','logged':'Int64','lo':'float64','lolo':'float64','hi':'float64',
                                    'hihi':'float64','discrete_alarm_value':'Int64'}) #снова приводим типы столбцов к нужным
    
    table_result["type"] = table_result["type"].astype(str).str.strip().str.lower() # на всякий случай нормализовать типы тегов
    
    table_result["name_copy"] = table_result["name"] 
    table_result["name_copy"] = table_result["name_copy"].astype(str).str.strip()
    tags_rename = {#убрать символы кириллицей, так как обязательно все имена тегов должны быть на латинице
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z','и':'i','й':'y',
        'к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f',
        'х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
        'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'Yo','Ж':'Zh','З':'Z','И':'I','Й':'Y',
        'К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F',
        'Х':'Kh','Ц':'Ts','Ч':'Ch','Ш':'Sh','Щ':'Shch','Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Yu','Я':'Ya',
        '\\':'_','-':'_',' ':'','/':'_'}
    table_result['name'] = (table_result['name'].astype(str).str.translate(str.maketrans(tags_rename)))

    # Заполнить системные столбцы
    table_result['initial_value'] = 0 # здесь всегда 0, значение при запуске
    table_result['access_type'] = 1 # здесь всегда 1, тип доступа
    table_result['logged'] = 0 # по умолчанию логирование везде выключено

    #tag_type
    type_1 = table_result["type"] != "discret"
    table_result.loc[type_1, "tag_type"] = 1 # type analog
    type_3 = table_result["type"] == "discret"
    table_result.loc[type_3, "tag_type"] = 3 #type discret

    # fire discret alarm
    table_result.loc[type_3, "discrete_alarm_value"] = 1

    table_result.loc[type_3, "dec"] = np.nan # у дискретников нет шкалы и нет dec
    table_result.loc[type_3, "scale_min"] = np.nan
    table_result.loc[type_3, "scale_max"] = np.nan

    type_app = table_result["type"] == "app" # расставить шкалу для аппаратов где не заполнено
    table_result.loc[type_app, "scale_min"] = table_result["scale_min"].fillna(0)
    table_result.loc[type_app, "scale_max"] = table_result["scale_max"].fillna(1)

    return table_result

def add_prefix(table_result,prefix): #имя тега не может начинаться с цифры, поэтому добавляем префик если нужно
    def func_prefix(x):
        x = str(x)
        if x[0].isdigit():
            return prefix + x
        else:
            return x
    table_result["name"] = table_result["name"].apply(func_prefix)
    return table_result

def add_pv(table_result):
    def func_pv(x):
        x = str(x)
        if not x.endswith("_PV"):
            return x + '_PV'
        else:
            return x
    table_result["name"] = table_result["name"].apply(func_pv)
    return table_result

def units_normalize(table_result):
    unit_rename = {
        "нм3/час": "нм3/ч",
        "кг/час" : "кг/ч",
        "кПа" : "КПа",
        "Мпа" : "МПа",
        "С": "°C",
        "C" : "°C",
        "м3/час": "м3/ч",}
    table_result['unit'] = table_result['unit'].replace(unit_rename)
    return table_result

def br_analog_func(table_result, br_num):
    br_analog = table_result[table_result["type"] == 'analog'].copy()
    br_analog['name'] = br_analog['name'].astype(str).str.replace("_PV", "_BR", regex=False)
    br_analog['desc'] = 'Поломки'
    br_analog['scale_min'] = 0
    br_analog['scale_max'] = br_num
    br_analog['dec'] = np.nan
    br_analog['lolo'] = np.nan
    br_analog['lo'] = np.nan
    br_analog['hi'] = np.nan
    br_analog['hihi'] = np.nan
    br_analog['unit'] = np.nan
    br_analog['type'] = 'br_analog'
    table_result = pd.concat([br_analog, table_result], ignore_index=True)
    return table_result

def br_reg_func(table_result, br_num):
    br_reg = table_result[table_result["type"] == 'reg'].copy()
    br_reg['name'] = br_reg['name'].astype(str).str.replace("_PV", "_BR", regex=False)
    br_reg['desc'] = 'Поломки'
    br_reg['scale_min'] = 0
    br_reg['scale_max'] = br_num
    br_reg['dec'] = np.nan
    br_reg['lolo'] = np.nan
    br_reg['lo'] = np.nan
    br_reg['hi'] = np.nan
    br_reg['hihi'] = np.nan
    br_reg['unit'] = np.nan
    br_reg['type'] = 'br_reg'
    table_result = pd.concat([br_reg, table_result], ignore_index=True)
    return table_result

def br_regc_func(table_result, br_num):
    brc_reg = table_result[table_result["type"] == 'reg'].copy()
    brc_reg['name'] = brc_reg['name'].astype(str).str.replace("_PV", "_BRC", regex=False)
    brc_reg['desc'] = 'Поломки'
    brc_reg['scale_min'] = 0
    brc_reg['scale_max'] = br_num
    brc_reg['dec'] = np.nan
    brc_reg['lolo'] = np.nan
    brc_reg['lo'] = np.nan
    brc_reg['hi'] = np.nan
    brc_reg['hihi'] = np.nan
    brc_reg['unit'] = np.nan
    brc_reg['type'] = 'brc_reg'
    table_result = pd.concat([brc_reg, table_result], ignore_index=True)
    return table_result

def br_discret_func(table_result, br_num_discr):
    br_discret = table_result[table_result["type"] == 'discret'].copy()
    br_discret['name'] = br_discret['name'].astype(str).str.replace("_PV", "_BR", regex=False)
    br_discret['desc'] = 'Поломки'
    br_discret['scale_min'] = 0
    br_discret['scale_max'] = br_num_discr
    br_discret['dec'] = np.nan
    br_discret['lolo'] = np.nan
    br_discret['lo'] = np.nan
    br_discret['hi'] = np.nan
    br_discret['hihi'] = np.nan
    br_discret['unit'] = np.nan
    br_discret['tag_type'] = 1
    br_discret['discrete_alarm_value'] = np.nan
    br_discret['type'] = 'br_discret'
    table_result = pd.concat([br_discret, table_result], ignore_index=True)
    return table_result

def br_device_func(table_result, br_num_app):
    br_device = table_result[table_result["type"] == 'app'].copy()
    br_device['name'] = br_device['name'].astype(str).str.replace("_PV", "_BR", regex=False)
    br_device['desc'] = 'Поломки'
    br_device['scale_min'] = 0
    br_device['scale_max'] = br_num_app
    br_device['dec'] = np.nan
    br_device['lolo'] = np.nan
    br_device['lo'] = np.nan
    br_device['hi'] = np.nan
    br_device['hihi'] = np.nan
    br_device['unit'] = np.nan
    br_device['type'] = 'br_device'
    table_result = pd.concat([br_device, table_result], ignore_index=True)
    return table_result

def add_tags_for_reg_func(table_result):
    sv_reg = table_result[table_result["type"] == 'reg'].copy()
    sv_reg['name'] = sv_reg['name'].astype(str).str.replace("_PV", "_SV", regex=False)
    sv_reg['type'] = 'sv_reg'
    sv_reg['lolo'] = np.nan
    sv_reg['lo'] = np.nan
    sv_reg['hi'] = np.nan
    sv_reg['hihi'] = np.nan

    mv_reg = table_result[table_result["type"] == 'reg'].copy()
    mv_reg['name'] = mv_reg['name'].astype(str).str.replace("_PV", "_MV", regex=False)
    mv_reg['scale_min'] = 0
    mv_reg['scale_max'] = 100
    mv_reg['dec'] = 1
    mv_reg['lolo'] = np.nan
    mv_reg['lo'] = np.nan
    mv_reg['hi'] = np.nan
    mv_reg['hihi'] = np.nan
    mv_reg['unit'] = '%'
    mv_reg['type'] = 'mv_reg'
    
    mode_reg = table_result[table_result["type"] == 'reg'].copy()
    mode_reg['name'] = mode_reg['name'].astype(str).str.replace("_PV", "_MODE", regex=False)
    mode_reg['scale_min'] = 0
    mode_reg['scale_max'] = 3
    mode_reg['dec'] = np.nan
    mode_reg['lolo'] = np.nan
    mode_reg['lo'] = np.nan
    mode_reg['hi'] = np.nan
    mode_reg['hihi'] = np.nan
    mode_reg['unit'] = np.nan
    mode_reg['type'] = 'mode_reg'
    table_result = pd.concat([mv_reg, table_result], ignore_index=True)
    table_result = pd.concat([sv_reg, table_result], ignore_index=True)
    table_result = pd.concat([mode_reg, table_result], ignore_index=True)
    return table_result

def logging_reg(table_result):
    table_result.loc[table_result["type"].isin(["reg", "sv_reg", "mv_reg"]),'logged'] = 1
    table_result.loc[table_result["type"] == 'analog','logged'] = 1
    return table_result

def app_mv_func(table_result):
    app_mv = table_result[table_result["type"] == 'app'].copy()
    app_mv['name'] = app_mv['name'].astype(str).str.replace("_PV", "_MV", regex=False)
    app_mv['type'] = 'app_mv'
    table_result = pd.concat([app_mv, table_result], ignore_index=True)
    return table_result

def app_mode_func(table_result):
    app_mode = table_result[table_result["type"] == 'app'].copy()
    app_mode['name'] = app_mode['name'].astype(str).str.replace("_PV", "_MODE", regex=False)
    app_mode['scale_min'] = 0
    app_mode['scale_max'] = 1
    app_mode['dec'] = np.nan
    app_mode['unit'] = np.nan
    app_mode['type'] = 'app_mode'
    table_result = pd.concat([app_mode, table_result], ignore_index=True)
    return table_result

def app_upr_func(table_result):
    app_upr = table_result[table_result["type"] == 'app'].copy()
    app_upr['name'] = app_upr['name'].astype(str).str.replace("_PV", "_UPR", regex=False)
    app_upr['scale_min'] = 0
    app_upr['scale_max'] = 1
    app_upr['dec'] = np.nan
    app_upr['unit'] = np.nan
    app_upr['type'] = 'app_upr'
    table_result = pd.concat([app_upr, table_result], ignore_index=True)
    return table_result

def app_paz_func(table_result):
    app_paz = table_result[table_result["type"] == 'app'].copy()
    app_paz['name'] = app_paz['name'].astype(str).str.replace("_PV", "_PAZ", regex=False)
    app_paz['scale_min'] = 0
    app_paz['scale_max'] = 1
    app_paz['dec'] = np.nan
    app_paz['unit'] = np.nan
    app_paz['type'] = 'app_paz'
    table_result = pd.concat([app_paz, table_result], ignore_index=True)
    return table_result

def convert_for_download(table_result):
    table_result = table_result.drop(columns=["name_copy", "type"], errors="ignore")
    table_result = table_result.drop_duplicates()
    return table_result


#РАБОТА С PROJECT.DB

def extract_alarm_columns(alarms):
    lst = {"lo": np.nan, "hi": np.nan, "lolo": np.nan, "hihi": np.nan, "discrete_alarm_value": np.nan}
    if alarms is None:
        return pd.Series(lst)
    
    if isinstance(alarms, bytes):
       alarms = alarms.decode("utf-8")
    if isinstance(alarms, str):
        alarms = json.loads(alarms)

    if not isinstance(alarms, list):
        return pd.Series(lst)
    
    for alarm in alarms:
        if not alarm.get("enabled", False):
            continue
        alarm_type = int(alarm.get("type"))

        if alarm_type == 1:
            lst["lo"] = alarm.get("value")
        elif alarm_type == 2:
            lst["hi"] = alarm.get("value")
        elif alarm_type == 3:
            lst["lolo"] = alarm.get("value")
        elif alarm_type == 4:
            lst["hihi"] = alarm.get("value")
        elif alarm_type == 6:
            lst["discrete_alarm_value"] = int(alarm.get("value"))
   
    return pd.Series(lst)

def load_tags_from_db(uploaded_db):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        tmp_file.write(uploaded_db.getbuffer())
        tmp_db_path = tmp_file.name
    conn = sqlite3.connect(tmp_db_path)
    tags = pd.read_sql_query("SELECT * FROM tags", conn)
    conn.close()
    alarm_columns = tags["alarm_set"].apply(extract_alarm_columns)
    for colmn in ["lo", "hi", "lolo", "hihi", "discrete_alarm_value"]:
        tags[colmn] = alarm_columns[colmn]
    return tags

def prepare_tags_for_download(tags):
    tags_dwnld = tags.drop(columns=["alarm_set", "id"], errors="ignore")
    return tags_dwnld


#ПРЕДОБРАБОТКА ТАБЛИЦЫ

def read_pre_file(taglist_file): # новый обработчик файлов так как нужно будет потом забрать знаки после запятой
    file_type = Path(taglist_file.name).suffix.lower()

    if file_type == ".csv":
        pre_table = pd.read_csv(taglist_file, dtype=str)
    elif file_type in [".xlsx", ".xls"]:
        pre_table = pd.read_excel(taglist_file, dtype=str)
    elif file_type == ".ods":
        pre_table = pd.read_excel(taglist_file, engine="odf", dtype=str)
    else:
        raise ValueError(f"Неподдерживаемый тип файла: {file_type}")

    return pre_table

def normalize_pre_table(pre_table):
    table = pd.DataFrame()
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if any(word in clmn_lower for word in ["tag", "name", "имя", "тег"]):
            table["name"] = pre_table.pop(clmn)
            break
    
    found_desc = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if any(word in clmn_lower for word in ["desc", "комментарий", "описание", "comm"]):
            table["desc"] = pre_table.pop(clmn)
            found_desc = True
            break
    if not found_desc:
        table["desc"] = np.nan

    found_max = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if any(word in clmn_lower for word in ["max", "мах", "sh"]):
            table["scale_max"] = pre_table.pop(clmn)
            found_max = True
            break
    if not found_max:
        table["scale_max"] = np.nan

    found_min = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if any(word in clmn_lower for word in ["min", "мин", "sl"]):
            table["scale_min"] = pre_table.pop(clmn)
            found_min = True
            break
    if not found_min:
        table["scale_min"] = np.nan

    found_unit = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if any(word in clmn_lower for word in ["unit", "ед"]):
            table["unit"] = pre_table.pop(clmn)
            found_unit = True
            break
    if not found_unit:
        table["unit"] = np.nan

    found_dec = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if any(word in clmn_lower for word in ["dec"]):
            table["dec"] = pre_table.pop(clmn)
            found_dec = True
            break
    if not found_dec:
        table["dec"] = np.nan

    found_lolo = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if "lolo" in clmn_lower or clmn_lower == "ll":
            table["lolo"] = pre_table.pop(clmn)
            found_lolo = True
            break
    if not found_lolo:
        table["lolo"] = np.nan

    found_lo = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if "lo" in clmn_lower or clmn_lower == "l":
            table["lo"] = pre_table.pop(clmn)
            found_lo = True
            break
    if not found_lo:
        table["lo"] = np.nan

    found_hihi = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if "hihi" in clmn_lower or clmn_lower == "hh":
            table["hihi"] = pre_table.pop(clmn)
            found_hihi = True
            break
    if not found_hihi:
        table["hihi"] = np.nan

    found_hi = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if "hi" in clmn_lower or clmn_lower == "h":
            table["hi"] = pre_table.pop(clmn)
            found_hi = True
            break
    if not found_hi:
        table["hi"] = np.nan

    found_type = False
    for clmn in list(pre_table.columns):
        clmn_lower = clmn.lower()
        if any(word in clmn_lower for word in ["type","тип"]):
            table["type"] = pre_table.pop(clmn)
            found_type = True
            break
    if not found_type:
        table["type"] = np.nan

    return table

def get_dec_from_row(row): # получение числа знаков после запятой
    col_for_dec = None 
    for clmn in row.index: 
        clmn_lower = clmn.lower() 
        if "min" in clmn_lower: 
            col_for_dec = clmn 
            break 
        if "max" in clmn_lower: 
            col_for_dec = clmn 
            if col_for_dec is None: 
                return 0 
            x = str(row[col_for_dec]).replace(",", ".") 
            if "." in x: 
                return len(x.split(".")[1]) 
            return 0
