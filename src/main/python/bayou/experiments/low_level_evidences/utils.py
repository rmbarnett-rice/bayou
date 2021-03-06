# Copyright 2017 Rice University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import argparse
import re
import json
import random
from itertools import chain
import tensorflow as tf

CONFIG_GENERAL = ['latent_size', 'batch_size', 'num_epochs',
                  'learning_rate', 'print_step', 'alpha', 'beta']
CONFIG_ENCODER = ['name', 'units', 'tile', 'max_num']
CONFIG_DECODER = ['units', 'max_ast_depth']
CONFIG_INFER = ['chars', 'vocab', 'vocab_size']

C0 = 'CLASS0'
UNK = '_UNK_'
CHILD_EDGE = 'V'
SIBLING_EDGE = 'H'


def length(tensor):
    elems = tf.sign(tf.reduce_max(tensor, axis=2))
    return tf.reduce_sum(elems, axis=1)


# split s based on camel case and lower everything (uses '#' for split)
def split_camel(s):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1#\2', s)  # UC followed by LC
    s1 = re.sub('([a-z0-9])([A-Z])', r'\1#\2', s1)  # LC followed by UC
    split = s1.split('#')
    return [s.lower() for s in split]


# Do not move these imports to the top, it will introduce a cyclic dependency
import bayou.experiments.low_level_evidences.evidence


# convert JSON to config
def read_config(js, chars_vocab=False):
    config = argparse.Namespace()

    for attr in CONFIG_GENERAL:
        config.__setattr__(attr, js[attr])
    
    config.evidence = bayou.experiments.low_level_evidences.evidence.Evidence.read_config(js['evidence'], chars_vocab)
    config.decoder = argparse.Namespace()
    for attr in CONFIG_DECODER:
        config.decoder.__setattr__(attr, js['decoder'][attr])
    if chars_vocab:
        for attr in CONFIG_INFER:
            config.decoder.__setattr__(attr, js['decoder'][attr])

    return config


# convert config to JSON
def dump_config(config):
    js = {}

    for attr in CONFIG_GENERAL:
        js[attr] = config.__getattribute__(attr)

    js['evidence'] = [ev.dump_config() for ev in config.evidence]
    js['decoder'] = {attr: config.decoder.__getattribute__(attr) for attr in
                     CONFIG_DECODER + CONFIG_INFER}

    return js


HELP = """Use this to extract evidences from a raw data file with sequences generated by driver.
You can also filter programs based on number and length of sequences, and control the samples from each program."""


def extract_evidence(clargs):
    print('Loading data file...', end='')
    with open(clargs.input_file[0]) as f:
        js = json.load(f)
    print('done')
    done = 0
    programs = []
    for program in js['programs']:
        sequences = program['sequences']
        if len(sequences) > clargs.max_seqs or \
                any([len(sequence['calls']) > clargs.max_seq_length for sequence in sequences]):
            continue

        calls = set(chain.from_iterable([sequence['calls'] for sequence in sequences]))

        apicalls = list(set(chain.from_iterable([bayou.experiments.low_level_evidences.evidence.APICalls.from_call(call) for call in calls])))
        types = list(set(chain.from_iterable([bayou.experiments.low_level_evidences.evidence.Types.from_call(call) for call in calls])))
        context = list(set(chain.from_iterable([bayou.experiments.low_level_evidences.evidence.Context.from_call(call) for call in calls])))

        if clargs.num_samples == 0:
            program['apicalls'] = apicalls
            program['types'] = types
            program['context'] = context
            programs.append(program)
        else:
            for i in range(clargs.num_samples):
                sample = dict(program)
                sample['apicalls'] = random.sample(apicalls, random.choice(range(len(apicalls) + 1)))
                sample['types'] = random.sample(types, random.choice(range(len(types) + 1)))
                sample['context'] = random.sample(context, random.choice(range(len(context) + 1)))
                if sample['apicalls'] == [] and sample['types'] == [] and sample['context'] == []:
                    continue
                programs.append(sample)

        done += 1
        print('Extracted evidence for {} programs'.format(done), end='\r')

    print('\nWriting to {}...'.format(clargs.output_file[0]), end='')
    with open(clargs.output_file[0], 'w') as f:
        json.dump({'programs': programs}, fp=f, indent=2)
    print('done')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=HELP)
    parser.add_argument('input_file', type=str, nargs=1,
                        help='input data file')
    parser.add_argument('output_file', type=str, nargs=1,
                        help='output data file')
    parser.add_argument('--max_seqs', type=int, default=9999,
                        help='maximum number of sequences in a program')
    parser.add_argument('--max_seq_length', type=int, default=9999,
                        help='maximum length of each sequence in a program')
    parser.add_argument('--num_samples', type=int, default=0,
                        help='number of samples of evidences per program')
    clargs = parser.parse_args()
    extract_evidence(clargs)
