import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO # для загрузки файла
from pathlib import Path # для определения расширения файла - путь файла

import sys
project_root = Path(__file__).resolve().parent.parent # без этого не видел папку бэкэнд
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from backend.processing import (read_file, normalize_tags_table,add_prefix, add_pv,units_normalize, br_analog_func,
                                br_reg_func, br_regc_func, br_device_func, br_discret_func, add_tags_for_reg_func,
                                logging_reg, app_mv_func, app_mode_func, app_upr_func, app_paz_func, convert_for_download)

st.markdown("Давай сделаем что-то с этим")

# Ввод имени
name_project = st.text_input("Ввести имя проекта:", placeholder="Проект")
name_system = st.text_input("Ввести систему управления:", placeholder="Система управления (например, Siemens, CentumVP, Delta V)")

uploaded_file = st.file_uploader("Загрузить файл", type=["csv", "xlsx", "xls", "ods"])
if uploaded_file is not None:
    tags_table = read_file(uploaded_file)
    table_result = normalize_tags_table(tags_table)
    #st.dataframe(table_result.head(20))

#col_1, col_2 = st.columns(2)

#with col_1:
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

if uploaded_file is not None:
    st.dataframe(table_result)
            
if st.button("Подготовить для скачивания"):
    tags_table_dnwl = convert_for_download(table_result)
    file_name = f"{name_project}_tags.csv"
    st.download_button(label="Скачать csv", data=tags_table_dnwl, file_name=file_name, mime="text/csv")

#with col_2:
 #   st.caption("One")
#st.caption("Two", divider=True)
#st.caption("Three", divider=True)
#st.caption(prefix, divider=True)
#st.markdown("This is a subheader with a divider")
#st.write("You selected:", options)
