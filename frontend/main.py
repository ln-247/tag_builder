import streamlit as st
import pandas as pd

from pathlib import Path # для определения расширения файла - путь файла

import sys


project_root = Path(__file__).resolve().parent.parent # без этого не видел папку бэкэнд
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from backend.processing import (read_file, normalize_tags_table,add_prefix, add_pv,units_normalize, br_analog_func,
                                br_reg_func, br_regc_func, br_device_func, br_discret_func, add_tags_for_reg_func,
                                logging_reg, app_mv_func, app_mode_func, app_upr_func, app_paz_func, convert_for_download,
                                load_tags_from_db, prepare_tags_for_download)

st.markdown("Давай сделаем что-то с этим")

tab1, tab2, tab3 = st.tabs(["Tag Builder", "Работа с project.db", "Групповые тренды"])
with tab1:
# Ввод имени
    name_project = st.text_input("Ввести имя проекта:", placeholder="Проект")
    name_system = st.text_input("Ввести систему управления:", placeholder="Система управления (например, Siemens, CentumVP, Delta V)")

    uploaded_file = st.file_uploader("Загрузить файл", type=["csv", "xlsx", "xls", "ods"])
    if uploaded_file is not None:
        tags_table = read_file(uploaded_file)
        table_result = normalize_tags_table(tags_table)
        #st.dataframe(table_result.head(20))

    prefix = st.text_input("Ввести префикc для тегов, начинающихся с цифры:", placeholder= "Например, K_ или M_")
    if prefix:
        table_result = add_prefix(table_result, prefix)

    pv = st.checkbox("Добавить PV")
    if pv:
        table_result = add_pv(table_result)

    # Нормализовать ед.измерения
    units = st.checkbox("Нормализовать ед.измерения")
    if units:
        table_result = units_normalize(table_result)

    # Поломки
    br = st.multiselect("Выбрать поломки:",["Датчик", "Регулятор (BR)","Регулятор (BRC)","Аппараты", "Дискретник"],)
    
    if br:
        if 'Датчик' in br or 'Регулятор (BR)' in br or 'Регулятор (BRC)' in br:
            br_num = st.number_input("Ввести количество поломок для датчика и регулятора:", min_value=0)
        if "Аппараты" in br:
            br_num_app = st.number_input("Ввести количество поломок для аппаратов:", min_value=0)
        if "Дискретник" in br:
            br_num_discr = st.number_input("Ввести количество поломок для дискретного тега:", min_value=0)

    if 'Датчик' in br and br_num != 0:
        table_result = br_analog_func(table_result, br_num)

    if 'Регулятор (BR)' in br and br_num != 0:
        table_result = br_reg_func(table_result, br_num)

    if 'Регулятор (BRC)' in br and br_num != 0:
        table_result = br_regc_func(table_result, br_num)

    if 'Аппараты' in br and br_num_app != 0:
        table_result = br_device_func(table_result, br_num_app)

    if "Дискретник" in br and br_num_discr != 0:
        table_result = br_discret_func(table_result, br_num_discr)

    # добавить mv, sv, mode
    add_tags_for_reg = st.checkbox("Добавить MV, SV, MODE для регулятора")
    if add_tags_for_reg:
        table_result = add_tags_for_reg_func(table_result)
   
   # Выставить логирование
    logs = st.checkbox("Выставить логирование для PV, MV, SV регулятора и PV датчика")
    if logs:
        table_result = logging_reg(table_result)

    # Добавить теги для аппаратов
    app_tags = st.multiselect("Добавить теги для аппаратов",["MV", "MODE","UPR","PAZ"],)
    
    if app_tags:
        if 'MV' in app_tags:
           table_result = app_mv_func(table_result)
        if 'MODE' in app_tags:
           table_result = app_mode_func(table_result)
        if 'UPR' in app_tags:
           table_result = app_upr_func(table_result)
        if 'PAZ' in app_tags:
           table_result = app_paz_func(table_result)   
            
    if st.button("Подготовить для скачивания"):
        tags_table_dnwl = convert_for_download(table_result)
        st.dataframe(tags_table_dnwl)
        table_result_csv = tags_table_dnwl.to_csv(index=False, sep=",").encode("utf-8")
        file_name = f"{name_project}_tags.csv"
        st.download_button(label="Скачать csv", data=table_result_csv, file_name=file_name, mime="text/csv")

with tab2:
    uploaded_db = st.file_uploader("Загрузить файл", type=["db"])
    if uploaded_db is not None:
        tags = load_tags_from_db(uploaded_db)
        
        if st.button("Подготовить для скачивания "):
            tags_dwnld = prepare_tags_for_download(tags)
            st.dataframe(tags_dwnld)
            csv_data = tags_dwnld.to_csv(index=False, sep=",").encode("utf-8")
            st.download_button(label="Скачать csv",data=csv_data,file_name="tags.csv",mime="text/csv")
        
        



    #db_path = r"H:\111\учеба\notebooks\tag_builder\project.db"
    