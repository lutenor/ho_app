# -*- coding: utf-8 -*-
"""
Created on Mon Oct 21 13:26:37 2019

@author: lgrueso
"""

import base64
import datetime
import io

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table

import pandas as pd
import ho_analysis_dash_funcs as hof

df = pd.DataFrame()
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

app.layout = html.Div([
    html.H6("Neighbor Hand-Over Analysis"), 
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop a NBR_HO_Analysis report in csv\
            or xlsx format from NetAct, or ',
            html.A('Select a File')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # 
        multiple=False
    ),
    html.Div(id='output-data-upload'),
    html.Div(id='output-data-ho_process'), # Add an html.Div for app output
])


def parse_contents(contents, filename, date):
    global df
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')), sep=';')
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
            df.drop(0, inplace=True)
            df[df.columns[14:]] = df[df.columns[14:]].astype('float')
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    upload_table_div =  html.Div([
        html.H5(filename),
        html.H6(datetime.datetime.fromtimestamp(date)),

        dash_table.DataTable(
            data=df.head().to_dict('records'), # modified to show head only
            columns=[{'name': i, 'id': i} for i in df.columns]
        ),
        html.Hr()
    ])
    
    
    return upload_table_div


    
@app.callback([Output('output-data-upload', 'children'),
               Output('output-data-ho_process', 'children')],
              [Input('upload-data', 'contents')],
              [State('upload-data', 'filename'),
               State('upload-data', 'last_modified')])
def update_database(content, name, date):
    upload_tb_list, ho_proc_list = [], []
    if content is not None:
        #for c, n, d in zip(list_of_contents, list_of_names, list_of_dates):
        upload_tb_div = parse_contents(content, name, date)
        # process_ho returns a div with the three plots inside
        ho_process_div = hof.process_ho(df) 
        
        upload_tb_list.append(upload_tb_div)
        ho_proc_list.append(ho_process_div)
        
    return upload_tb_list, ho_proc_list
        
        # upload_table = [
        #     parse_contents(c, n, d)[0] for c, n, d in
        #     zip(list_of_contents, list_of_names, list_of_dates)]
        # return upload_table

#print("Is this run before files are uploaded?")

if __name__ == '__main__':
    app.run_server(debug=True)
