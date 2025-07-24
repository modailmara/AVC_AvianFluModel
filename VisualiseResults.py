import seaborn as sns
import pandas as pd
import matplotlib

matplotlib.use('TkAgg')


def visualise_paths(result_list):
    """

    :param result_list:
    :type result_list: List[Dict{str, Any}]
    """
    # create the pandas DataFrame
    path_dict = {'path': [], 'iteration': [], 'count': []}
    end_comm_path_dict = {'path': [], 'iteration': [], 'count': []}
    not_start_comm_end_comm_path_dict = {'path': [], 'iteration': [], 'count': []}
    for iteration_dict in result_list:
        for path_tuple, path_count in iteration_dict['paths'].items():
            path = '-'.join(path_tuple)

            path_dict['path'].append(path)
            path_dict['iteration'].append(iteration_dict['iteration'])
            path_dict['count'].append(path_count)
            # only add paths that end in community
            if path_tuple[-1] == 'community' and path_count > 0:
                end_comm_path_dict['path'].append(path)
                end_comm_path_dict['iteration'].append(iteration_dict['iteration'])
                end_comm_path_dict['count'].append(path_count)
                if path_tuple[0] != 'community':
                    not_start_comm_end_comm_path_dict['path'].append(path)
                    not_start_comm_end_comm_path_dict['iteration'].append(iteration_dict['iteration'])
                    not_start_comm_end_comm_path_dict['count'].append(path_count)

    # path_df = pd.DataFrame(data=path_dict)
    print('path: {}'.format(path_dict))
    print('end: {}'.format(end_comm_path_dict))
    print('not start: {}'.format(not_start_comm_end_comm_path_dict))

    # make charts
    sns.set_theme(rc={'figure.figsize': (10, 50)})

    if len(path_dict['path']) > 0:
        path_plot = sns.catplot(data=path_dict, x='count', y='path', kind='box',
                                height=20, aspect=1)
        path_plot.savefig('./visualisations/path_barplot_all.png')
    else:
        print('No paths')

    if len(end_comm_path_dict['path']) > 0:
        path_plot = sns.catplot(data=end_comm_path_dict, x='count', y='path', kind='box',
                                height=20, aspect=1)
        path_plot.savefig('./visualisations/path_barplot_community.png')
    else:
        print('No paths ending in community')

    if len(not_start_comm_end_comm_path_dict['path']) > 0:
        path_plot = sns.catplot(data=not_start_comm_end_comm_path_dict, x='count', y='path', kind='box',
                                height=20, aspect=1)
        path_plot.savefig('./visualisations/path_barplot_not_start_community.png')
    else:
        print('No paths not starting in community, but ending in community')