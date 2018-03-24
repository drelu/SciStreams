"""
    This DAG is the primary DAG. It will:
        - pick out images from the stream from detectors.
        - ensure that the attributes coming in have all needed keys
            If they don't, it won'process them

        - This spawns the one_image_dag DAG for events
            with the images expected and attributes
"""

from lightflow.models import Dag
from lightflow.tasks import PythonTask
from lightflow.models.task_data import TaskData, MultiTaskData

# TODO : make callback something else callback
# 
from databroker import Broker
import matplotlib.pyplot as plt
import numpy as np

from SciStreams.workflows.one_image import one_image_dag


# filter a streamdoc with certain attributes (set in the yml file)
# required_attributes, typesdict globals needed
def filter_attributes(attr, type='main'):
    '''
        Filter attributes.

        Note that this ultimately checks that attributes match what is seen in
        yml file.
    '''
    from SciStreams.config import required_attributes, typesdict
    #print("filterting attributes")
    # get the sub required attributes
    reqattr = required_attributes['main']
    for key, val in reqattr.items():
        if key not in attr:
            print("bad attributes")
            print("{} not in attributes".format(key))
            return False
        elif not isinstance(attr[key], typesdict[val]):
            print("bad attributes")
            print("key {} not an instance of {}".format(key, val))
            return False
    #print("good attributes")
    return True



# this splits images into one image to send to tasks
def primary_func(data, store, signal, context):
    run_start = data['run_start']
    # md is also 'start'
    md = data['md']
    dbname = data['dbname']
    descriptor = data['descriptor']
    event = data['event']

    db = Broker.named(dbname)
    hdr = db[run_start]

    # pull the strema name
    stream_name = descriptor['name']

    fields = hdr.fields(stream_name)

    print("looking for an image with keys {}".format(fields))
    dag_names = list()
    # eventually iterate and spawn new tasks
    detector_keys = ['pilatus2M_image']
    for detector_key in detector_keys:
        if detector_key in fields:
            print("Found , saving an image")
            try:
                imgs = hdr.data(detector_key, fill=True)
                for img in imgs:
                    # give it some provenance and data
                    new_data = dict(img=img)
                    new_data['run_start'] = run_start
                    new_data['md'] = md.copy()
                    new_data['md']['detector_key'] = detector_key
                    new_data['descriptor'] = descriptor
                    new_data = TaskData(data=new_data)
                    new_data = MultiTaskData(dataset=new_data)
                    good_attr = filter_attributes(new_data['md'])
                    if good_attr:
                        print("got a good image")
                        dag_name = signal.start_dag(one_image_dag, data=new_data)
                        print("primary node, dag name: {}".format(dag_name))
                        dag_names.append(dag_name)
            except FileNotFoundError as exc:
                print("Error, could not find file, ignoring...")
                print(exc)
    signal.join_dags(dag_names)

# create the main DAG that spawns others
#img_dag = Dag('img_dag')
image_task = PythonTask(name="main",
                       callback=primary_func)
primary_dag_dict = {
    image_task: None,
    }

primary_dag = Dag("primary", autostart=False)
primary_dag.define(primary_dag_dict)
