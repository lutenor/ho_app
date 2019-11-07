import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import os
import dash_core_components as dcc
import dash_html_components as html


pio.renderers.default = "browser"


# ===== Get the .csv and  in the current directory  fuction ========
def get_xlsx_file():
    print("=== Getting input files === \n\n")
    path = os.getcwd()
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if ".xlsx" in filename:
                xlsx_file = filename
    return xlsx_file


# ================ Get worst HO neighbors ===========

def find_rank_worst_ho(ho_df):
    print("=== Ranking worst HO Neigbors === \n\n")
    # Get the file path:
    # path = os.getcwd()

    nbr = ho_df
    nbr['Target LNBTS ID'] = nbr['eci_id'] / 256
    nbr['Target LNBTS ID'] = nbr['Target LNBTS ID'].astype('int64')
    nbr['Target LCR ID'] = nbr['eci_id'] % 256

    # Drop unused columns:
    nbr.drop(['Source PLMN name', 'Source MRBTS name',
              'Target PLMN name', 'Target MRBTS name',
              'Target LNBTS name', 'Target LNCEL name',
              'Target LNCEL TAC', 'mcc_id', 'mnc_id',
              'dmcc_id', 'dmnc_id'], axis=1, inplace=True)

    # Build the pivot table:
    nbr_pivot = nbr.pivot_table(index=['Target LNBTS ID', 'Target LCR ID'],
                                aggfunc={'NBR Inter eNB Total HOSR': np.mean,
                                         'NBR Inter eNB HO Prep SR': np.mean,
                                         'NBR Inter eNB Ho Exec SR': np.mean,
                                         'NBR Inter eNB HO Preparations':
                                             np.sum,
                                         'INTER_HO_ATT_NB (M8015C8)': np.sum,
                                         'INTER_HO_SUCC_NB (M8015C9)': np.sum})

    # discard stats for low traffic:
    removal_limit = 0.001 * nbr_pivot['NBR Inter eNB HO Preparations'].sum()
    nbr_pivot_filtered = nbr_pivot[nbr_pivot['NBR Inter eNB HO Preparations']
                                   > removal_limit]

    # Sort table to put worst targets on top:
    nbr_piv_filt_sort \
        = nbr_pivot_filtered.sort_values(by=['NBR Inter eNB Total HOSR',
                                         'NBR Inter eNB HO Preparations'],
                                         ascending=[True, False])

    # Filter the worst 20 target cells:
    bad_cells = nbr_piv_filt_sort.head(20)

    return bad_cells


# ================ Neighbors Geo-location ===========

def neighbors_geo(bad_cells, site_locations_file_name, source_mrbts):
    '''Receives a bad-cells ranked dataframe, a file with Cascade coordinates
    (Sheet4), MRBT-Cascade mapping (Sheet5), the source MRBTS, and returns a df
    with geo-located MRBTS'''

    print("=== Geolocating bad neighbors === \n\n")

    set1 = set(bad_cells.index.get_level_values(0))
    bad_mrbts = pd.DataFrame(set1, columns=['MRBTS'])
    bad_mrbts['Target'] = 'Yes'

    # Add the source MRBTS
    bad_mrbts = bad_mrbts.append({'MRBTS': source_mrbts, 'Target': 'No'},
                                 ignore_index=True)

    # Read MRBTS-Cascade file
    mr_cas_df = pd.read_excel(site_locations_file_name,
                              sheet_name='MRBTS-Cascade')
    # Read Cascade coordinates file
    cas_coor_df = pd.read_excel(site_locations_file_name,
                                sheet_name='Cascade Coordinates')

    # Merge Cascade df to a MRBTS df with bad-cells' MRBTS
    bad_mrbts = pd.merge(bad_mrbts, mr_cas_df, how='left', on='MRBTS')
    # Merge Coordinates df to a MRBTS df with bad-cells' MRBTS
    bad_mrbts = pd.merge(bad_mrbts, cas_coor_df, how='left', on='Cascade')

    return bad_mrbts


# ================ Neighbors Map visualization ===========

def plot_ho(df):
    '''receives geo-located MRBS and shows (return) a plotly figure'''

    print("=== Building Map visualization === \n\n")
    fig = px.scatter_mapbox(df, lat='latitude', lon='longitude',
                            color="Target", zoom=11, height=500,
                            hover_data=['Cascade', 'MRBTS'])
    fig.update_layout(mapbox_style="carto-positron",
                      margin={"r": 0, "t": 30, "l": 0, "b": 0},
                      title_text="Source site and worst neighbors")

    return fig


#  ============= Show Table function ===========================

def draw_table(table, reset_index, table_title):

    print("=== Creating table === \n\n")

    if reset_index:
        table.reset_index(inplace=True)

    fig = go.Figure(data=[go.Table(
                    header=dict(values=list(table.columns),
                                fill_color='paleturquoise',
                                align='left'),
                    cells=dict(values=table.values.T,
                               fill_color='lavender',
                               align='left'))
    ])

    fig.update_layout(margin={"r": 0, "t": 30, "l": 0, "b": 0},
                      title_text=table_title)
    fig.update_layout(height=500)

    return fig


# =================== MAIN function =====================================

def process_ho(ho_df):
    
    my_xlsx = get_xlsx_file()
    source_mrbts = ho_df['Source LNBTS name'][1]
    if type(source_mrbts) == str:
        source_mrbts = int(source_mrbts[-7:])

    
    #file = open('NBR_analysis.htm', mode='a')
    
    bad_cells = find_rank_worst_ho(ho_df)
    bad_mrbts = neighbors_geo(bad_cells, my_xlsx, source_mrbts)
    
    geo_fig = plot_ho(bad_mrbts)
    geo_table_title = 'MRBTS / Cascade coordinates'
    bad_c_table_title = 'Cells with worst HOSR in ascending order'
    geo_summ_fig = draw_table(bad_mrbts, False, geo_table_title)
    bad_cells_fig = draw_table(bad_cells, True, bad_c_table_title)

    return html.Div(children=[dcc.Graph(id='geo_plot',figure=geo_fig),
                              html.Hr(),
                              dcc.Graph(id='bad_cells',figure=bad_cells_fig),
                              html.Hr(),
                              dcc.Graph(id='geo_summ',figure=geo_summ_fig)
                              ]
                    )


# Start dash:

'''
app = dash.Dash()
server = app.server
app.layout = html.Div(children=[dcc.Graph(id='geo_plot',figure=geo_fig),
                                dcc.Graph(id='bad_cells',figure=bad_cells_fig),
                                dcc.Graph(id='geo_summ',figure=geo_summ_fig)
                                ]
                      )


if __name__ == '__main__':
    app.run_server(debug=True)

# To be removed:
# geo_fig.write_html(file, full_html=False, include_plotlyjs=True)
# bad_cells_fig.write_html(file, full_html=False, include_plotlyjs=False)
# geo_summ_fig.write_html(file, full_html=False, include_plotlyjs=False)

# file.close()
print("=== Dashbord done === \n\n")
'''

