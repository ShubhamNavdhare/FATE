#
#  Copyright 2019 The FATE Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import argparse
import json

from pipeline.backend.pipeline import PipeLine
from pipeline.component.dataio import DataIO
from pipeline.component.evaluation import Evaluation
from pipeline.component.intersection import Intersection
from pipeline.component.reader import Reader
from pipeline.interface.data import Data
from pipeline.interface.model import Model
from pipeline.component.data_statistics import DataStatistics
from pipeline.runtime.entity import JobParameters
from pipeline.utils.tools import load_job_config


def prettify(response, verbose=True):
    if verbose:
        print(json.dumps(response, indent=4, ensure_ascii=False))
        print()
    return response


def main(config="../../config.yaml", namespace=""):
    if isinstance(config, str):
        config = load_job_config(config)
    backend = config.backend
    work_mode = config.work_mode
    parties = config.parties
    guest = parties.guest[0]
    hosts = parties.host[0]

    guest_train_data = {"name": "breast_hetero_guest", "namespace": f"experiment{namespace}"}
    host_train_data = {"name": "breast_hetero_host", "namespace": f"experiment{namespace}"}
    # guest_train_data = {"name": "default_credit_hetero_guest", "namespace": f"experiment{namespace}"}
    # host_train_data = {"name": "default_credit_hetero_host", "namespace": f"experiment{namespace}"}

    # initialize pipeline
    pipeline = PipeLine()
    # set job initiator
    pipeline.set_initiator(role='guest', party_id=guest)
    # set participants information
    pipeline.set_roles(guest=guest, host=hosts)

    # define Reader components to read in data
    reader_0 = Reader(name="reader_0")
    # configure Reader for guest
    reader_0.get_party_instance(role='guest', party_id=guest).component_param(table=guest_train_data)
    # configure Reader for host
    reader_0.get_party_instance(role='host', party_id=hosts).component_param(table=host_train_data)

    dataio_0 = DataIO(name="dataio_0", output_format='dense')

    # get DataIO party instance of guest
    dataio_0_guest_party_instance = dataio_0.get_party_instance(role='guest', party_id=guest)
    # configure DataIO for guest
    dataio_0_guest_party_instance.component_param(with_label=True)
    # get and configure DataIO party instance of host
    dataio_0.get_party_instance(role='host', party_id=hosts).component_param(with_label=False)

    # define Intersection components
    intersection_0 = Intersection(name="intersection_0")

    pipeline.add_component(reader_0)

    pipeline.add_component(dataio_0, data=Data(data=reader_0.output.data))

    pipeline.add_component(intersection_0, data=Data(data=dataio_0.output.data))

    statistic_param = {
        "name": "statistic_0",
        "statistics": ["95%", "coefficient_of_variance", "stddev"],
        "column_indexes": [1, 2],
        "column_names": []
    }
    statistic_0 = DataStatistics(**statistic_param)
    pipeline.add_component(statistic_0, data=Data(data=intersection_0.output.data))

    pipeline.compile()

    # fit model
    job_parameters = JobParameters(backend=backend, work_mode=work_mode)
    pipeline.fit(job_parameters)
    # query component summary
    prettify(pipeline.get_component("statistic_0").get_summary())


if __name__ == "__main__":
    parser = argparse.ArgumentParser("PIPELINE DEMO")
    parser.add_argument("-config", type=str,
                        help="config file")
    args = parser.parse_args()
    if args.config is not None:
        main(args.config)
    else:
        main()
