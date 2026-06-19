import streamlit as st
import pandas as pd

import requests

from pathlib import Path # для определения расширения файла - путь файла

import sys

API_URL = 'http://127.0.0.1:8000'


project_root = Path(__file__).resolve().parent.parent # без этого не видел папку бэкэнд
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

import backend.processing as pr 


st.markdown('Давай сделаем что-то с этим')

tab1, tab2, tab3, tab4 = st.tabs(['Предобработка таблицы', 'Tag Builder', 'Работа с project.db', 'Обновления и обратная связь'])
  
# ПОДГОТОВКА ТАБЛИЦЫ 

with tab1:
    uploaded_file_2 = st.file_uploader('Загрузить файл ', type=['csv', 'xlsx', 'xls', 'ods'])

    if uploaded_file_2 is not None:
        pre_table = pr.read_pre_file(uploaded_file_2)

        table = pr.normalize_pre_table(pre_table)
        dec = st.checkbox('Рассчитать знаки после запятой')
        if dec:
            table['dec'] = table.apply(pr.get_dec_from_row, axis=1) 

        if st.button('Подготовить для скачивания '):
                st.dataframe(table)
                pre_table_result_csv = table.to_csv(index=False, sep=',').encode('utf-8')
                file_name = 'tags.csv'
                st.download_button(label='Скачать csv', data=pre_table_result_csv, file_name=file_name, mime='text/csv')
    
#TAG BUILDER

with tab2:
# Ввод имени
    name_project = st.text_input('Ввести имя проекта:', placeholder='Проект')
    name_system = st.text_input('Ввести систему управления:', placeholder='Система управления (например, Siemens, CentumVP, DeltaV)')

    uploaded_file = st.file_uploader('Загрузить файл', type=['csv', 'xlsx', 'xls', 'ods'])
    if uploaded_file is not None:
        tags_table = pr.read_file(uploaded_file)
        table_result = pr.normalize_tags_table(tags_table)
    

        prefix = st.text_input('Ввести префикc для тегов, начинающихся с цифры:', placeholder= 'Например, K_ или M_')
        if prefix:
            table_result = pr.add_prefix(table_result, prefix)

        pv = st.checkbox('Добавить PV')
        if pv:
            table_result = pr.add_pv(table_result)

        # Нормализовать ед.измерения
        units = st.checkbox('Нормализовать ед.измерения')
        if units:
            table_result = pr.units_normalize(table_result)

        # Поломки
        br = st.multiselect('Выбрать поломки:',['Датчик', 'Регулятор (BR)','Регулятор (BRC)','Аппараты', 'Дискретник'],)
        
        if br:
            if 'Датчик' in br or 'Регулятор (BR)' in br or 'Регулятор (BRC)' in br:
                br_num = st.number_input('Ввести количество поломок для датчика и регулятора:', min_value=0)
            if 'Аппараты' in br:
                br_num_app = st.number_input('Ввести количество поломок для аппаратов:', min_value=0)
            if 'Дискретник' in br:
                br_num_discr = st.number_input('Ввести количество поломок для дискретного тега:', min_value=0)

        if 'Датчик' in br and br_num != 0:
            table_result = pr.br_analog_func(table_result, br_num)

        if 'Регулятор (BR)' in br and br_num != 0:
            table_result = pr.br_reg_func(table_result, br_num)

        if 'Регулятор (BRC)' in br and br_num != 0:
            table_result = pr.br_regc_func(table_result, br_num)

        if 'Аппараты' in br and br_num_app != 0:
            table_result = pr.br_device_func(table_result, br_num_app)

        if 'Дискретник' in br and br_num_discr != 0:
            table_result = pr.br_discret_func(table_result, br_num_discr)

        # добавить mv, sv, mode
        add_tags_for_reg = st.checkbox('Добавить MV, SV, MODE для регулятора')
        if add_tags_for_reg:
            table_result = pr.add_tags_for_reg_func(table_result)
    
    # Выставить логирование
        logs = st.checkbox('Выставить логирование для PV, MV, SV регулятора и PV датчика')
        if logs:
            table_result = pr.logging_reg(table_result)

        # Добавить теги для аппаратов
        app_tags = st.multiselect('Добавить теги для аппаратов:',['MV', 'MODE','UPR','PAZ'],)
        
        if app_tags:
            if 'MV' in app_tags:
                table_result = pr.app_mv_func(table_result)
            if 'MODE' in app_tags:
                table_result = pr.app_mode_func(table_result)
            if 'UPR' in app_tags:
             table_result = pr.app_upr_func(table_result)
            if 'PAZ' in app_tags:
                table_result = pr.app_paz_func(table_result)   
                
        if st.button('Подготовить для скачивания'):
            tags_table_dnwl = pr.convert_for_download(table_result)
            st.dataframe(tags_table_dnwl)
            table_result_csv = tags_table_dnwl.to_csv(index=False, sep=',').encode('utf-8')
            file_name = f'{name_project}_tags.csv'
            st.download_button(label='Скачать csv', data=table_result_csv, file_name=file_name, mime='text/csv')

#РАБОТА С PROJECT.DB

with tab3:
    uploaded_db = st.file_uploader('Загрузить файл', type=['db'])
    if uploaded_db is not None:
        tags = pr.load_tags_from_db(uploaded_db)
        
        if st.button('Подготовить для скачивания   '):
            tags_dwnld = pr.prepare_tags_for_download(tags)
            st.dataframe(tags_dwnld)
            csv_data = tags_dwnld.to_csv(index=False, sep=',').encode('utf-8')
            st.download_button(label='Скачать csv',data=csv_data,file_name='tags.csv',mime='text/csv')

# ОБРАТНАЯ СВЯЗЬ

if 'feedback_df' not in st.session_state: # добавим, чтобы не затиралось при каком-то действии
    st.session_state.feedback_df = None
with tab4:
    with st.form(' '):
        name_human = st.text_input('Ввести имя:') 
        name_project_fb = st.text_input('Ввести имя проекта: ')
        name_system_fb = st.text_input('Ввести систему управления: ')
        message_fb = st.text_area('Ввести сообщение:')
        
        submit_button = st.form_submit_button(label='Отправить')

    if submit_button:
        if message_fb.strip() == '':
            st.warning('Сообщение не должно быть пустым')
        else:
            feedback_data = {
                'name_human': name_human,
                'name_project': name_project_fb,
                'name_system': name_system_fb,
                'message': message_fb}

            try:
                response = requests.post(
                    f'{API_URL}/feedback',
                    json=feedback_data,
                    timeout=5)
                if response.status_code == 200:
                    st.success('Сообщение сохранено через API')
                else:
                    st.error(f'Ошибка API: {response.text}')

            except requests.exceptions.RequestException as error:
                st.error(f'Не удалось подключиться к backend: {error}')
    st.divider()

    if st.button('Посмотреть текущие отзывы'):
        try:
            response = requests.get(
                f'{API_URL}/feedback',
                timeout=5)
            if response.status_code == 200:
                feedback_list = response.json()
                if len(feedback_list) == 0:
                    st.info('Пока нет сохранённых отзывов')
                    st.session_state.feedback_df = None
                else:
                    st.session_state.feedback_df = pd.DataFrame(feedback_list)
            else:
                st.error(f'Ошибка API: {response.text}')

        except requests.exceptions.RequestException as error:
            st.error(f'Не удалось подключиться к backend: {error}')
    
    if st.session_state.feedback_df is not None:
        st.dataframe(
            st.session_state.feedback_df,
            use_container_width=True)





