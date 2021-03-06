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

import tensorflow as tf
import numpy as np
import os
import re
import json
from collections import Counter

from bayou.experiments.low_level_evidences.utils import CONFIG_ENCODER, CONFIG_INFER, C0, UNK


class Evidence(object):

    def init_config(self, evidence, chars_vocab):
        for attr in CONFIG_ENCODER + (CONFIG_INFER if chars_vocab else []):
            self.__setattr__(attr, evidence[attr])

    def dump_config(self):
        js = {attr: self.__getattribute__(attr) for attr in CONFIG_ENCODER + CONFIG_INFER}
        return js

    @staticmethod
    def read_config(js, chars_vocab):
        evidences = []
        for evidence in js:
            name = evidence['name']
            if name == 'apicalls':
                e = APICalls()
            elif name == 'types':
                e = Types()
            elif name == 'context':
                e = Context()
            else:
                raise TypeError('Invalid evidence name: {}'.format(name))
            e.init_config(evidence, chars_vocab)
            evidences.append(e)
        return evidences

    def read_data_point(self, program):
        raise NotImplementedError('read_data() has not been implemented')

    def set_chars_vocab(self, data):
        raise NotImplementedError('set_chars_vocab() has not been implemented')

    def wrangle(self, data):
        raise NotImplementedError('wrangle() has not been implemented')

    def placeholder(self, config):
        raise NotImplementedError('placeholder() has not been implemented')

    def exists(self, inputs):
        raise NotImplementedError('exists() has not been implemented')

    def init_sigma(self, config):
        raise NotImplementedError('init_sigma() has not been implemented')

    def encode(self, inputs, config):
        raise NotImplementedError('encode() has not been implemented')

    def evidence_loss(self, psi, encoding, config):
        raise NotImplementedError('evidence_loss() has not been implemented')


class APICalls(Evidence):

    def read_data_point(self, program):
        apicalls = program['apicalls'] if 'apicalls' in program else []
        return list(set(apicalls))

    def set_chars_vocab(self, data):
        counts = Counter([c for apicalls in data for c in apicalls])
        self.chars = sorted(counts.keys(), key=lambda w: counts[w], reverse=True)
        self.vocab = dict(zip(self.chars, range(len(self.chars))))
        self.vocab_size = len(self.vocab)

    def wrangle(self, data):
        wrangled = np.zeros((len(data), self.max_num, self.vocab_size), dtype=np.int32)
        for i, apicalls in enumerate(data):
            for j, c in enumerate(apicalls):
                if c in self.vocab:
                    wrangled[i, j, self.vocab[c]] = 1
        return wrangled

    def placeholder(self, config):
        return tf.placeholder(tf.float32, [config.batch_size, self.max_num, self.vocab_size])

    def exists(self, inputs):
        i = tf.reduce_sum(inputs, axis=2)
        return tf.not_equal(tf.count_nonzero(i, axis=1), 0)

    def init_sigma(self, config):
        with tf.variable_scope('apicalls'):
            self.sigma = tf.get_variable('sigma', [])

    def encode(self, inputs, config):
        with tf.variable_scope('apicalls'):
            latent_encoding = tf.zeros([config.batch_size, config.latent_size])
            for i in range(self.max_num):
                inp = tf.slice(inputs, [0, i, 0], [config.batch_size, 1, self.vocab_size])
                inp = tf.reshape(inp, [-1, self.vocab_size])
                encoding = tf.layers.dense(inp, self.units)
                w = tf.get_variable('w{}'.format(i), [self.units, config.latent_size])
                b = tf.get_variable('b{}'.format(i), [config.latent_size])
                latent_encoding += tf.nn.xw_plus_b(encoding, w, b)
            return latent_encoding

    def evidence_loss(self, psi, encoding, config):
        sigma_sq = tf.square(self.sigma)
        loss = 0.5 * (config.latent_size * tf.log(2 * np.pi * sigma_sq + 1e-10)
                      + tf.square(encoding - psi) / sigma_sq)
        return loss

    @staticmethod
    def from_call(call):
        split = call.split('(')[0].split('.')
        cls, name = split[-2:]
        return [name] if not cls == name else []


class Types(Evidence):

    def read_data_point(self, program):
        types = program['types'] if 'types' in program else []
        return list(set(types))

    def set_chars_vocab(self, data):
        counts = Counter([t for types in data for t in types])
        self.chars = sorted(counts.keys(), key=lambda w: counts[w], reverse=True)
        self.vocab = dict(zip(self.chars, range(len(self.chars))))
        self.vocab_size = len(self.vocab)

    def wrangle(self, data):
        wrangled = np.zeros((len(data), self.max_num, self.vocab_size), dtype=np.int32)
        for i, types in enumerate(data):
            for j, t in enumerate(types):
                if t in self.vocab:
                    wrangled[i, j, self.vocab[t]] = 1
        return wrangled

    def placeholder(self, config):
        return tf.placeholder(tf.float32, [config.batch_size, self.max_num, self.vocab_size])

    def exists(self, inputs):
        i = tf.reduce_sum(inputs, axis=2)
        return tf.not_equal(tf.count_nonzero(i, axis=1), 0)

    def init_sigma(self, config):
        with tf.variable_scope('types'):
            self.sigma = tf.get_variable('sigma', [])

    def encode(self, inputs, config):
        with tf.variable_scope('types'):
            latent_encoding = tf.zeros([config.batch_size, config.latent_size])
            for i in range(self.max_num):
                inp = tf.slice(inputs, [0, i, 0], [config.batch_size, 1, self.vocab_size])
                inp = tf.reshape(inp, [-1, self.vocab_size])
                encoding = tf.layers.dense(inp, self.units)
                w = tf.get_variable('w{}'.format(i), [self.units, config.latent_size])
                b = tf.get_variable('b{}'.format(i), [config.latent_size])
                latent_encoding += tf.nn.xw_plus_b(encoding, w, b)
            return latent_encoding

    def evidence_loss(self, psi, encoding, config):
        sigma_sq = tf.square(self.sigma)
        loss = 0.5 * (config.latent_size * tf.log(2 * np.pi * sigma_sq + 1e-10)
                      + tf.square(encoding - psi) / sigma_sq)
        return loss

    @staticmethod
    def from_call(call):
        split = list(reversed([q for q in call.split('(')[0].split('.')[:-1] if q[0].isupper()]))
        return [split[1], split[0]] if len(split) > 1 else [split[0]]


class Context(Evidence):

    def read_data_point(self, program):
        context = program['context'] if 'context' in program else []
        return list(set(context))

    def set_chars_vocab(self, data):
        counts = Counter([c for context in data for c in context])
        self.chars = sorted(counts.keys(), key=lambda w: counts[w], reverse=True)
        self.vocab = dict(zip(self.chars, range(len(self.chars))))
        self.vocab_size = len(self.vocab)

    def wrangle(self, data):
        wrangled = np.zeros((len(data), self.max_num, self.vocab_size), dtype=np.int32)
        for i, context in enumerate(data):
            for j, c in enumerate(context):
                if c in self.vocab:
                    wrangled[i, j, self.vocab[c]] = 1
        return wrangled

    def placeholder(self, config):
        return tf.placeholder(tf.float32, [config.batch_size, self.max_num, self.vocab_size])

    def exists(self, inputs):
        i = tf.reduce_sum(inputs, axis=2)
        return tf.not_equal(tf.count_nonzero(i, axis=1), 0)

    def init_sigma(self, config):
        with tf.variable_scope('context'):
            self.sigma = tf.get_variable('sigma', [])

    def encode(self, inputs, config):
        with tf.variable_scope('context'):
            latent_encoding = tf.zeros([config.batch_size, config.latent_size])
            for i in range(self.max_num):
                inp = tf.slice(inputs, [0, i, 0], [config.batch_size, 1, self.vocab_size])
                inp = tf.reshape(inp, [-1, self.vocab_size])
                encoding = tf.layers.dense(inp, self.units)
                w = tf.get_variable('w{}'.format(i), [self.units, config.latent_size])
                b = tf.get_variable('b{}'.format(i), [config.latent_size])
                latent_encoding += tf.nn.xw_plus_b(encoding, w, b)
            return latent_encoding

    def evidence_loss(self, psi, encoding, config):
        sigma_sq = tf.square(self.sigma)
        loss = 0.5 * (config.latent_size * tf.log(2 * np.pi * sigma_sq + 1e-10)
                      + tf.square(encoding - psi) / sigma_sq)
        return loss

    @staticmethod
    def from_call(call):
        args = call.split('(')[1].split(')')[0].split(',')
        args = [arg.split('.')[-1] for arg in args]
        args = [re.sub('<.*', r'', arg) for arg in args]  # remove generics
        args = [re.sub('\[\]', r'', arg) for arg in args]  # remove array type
        return [arg for arg in args if not arg == '']


# TODO: handle Javadoc with word2vec
class Javadoc(Evidence):

    def read_data_point(self, program, infer=False):
        javadoc = program['javadoc'] if 'javadoc' in program else None
        if not javadoc:
            javadoc = UNK
        try:  # do not consider non-ASCII javadoc
            javadoc.encode('ascii')
        except UnicodeEncodeError:
            javadoc = UNK
        javadoc = javadoc.split()
        return javadoc

    def set_dicts(self, data):
        if self.pretrained_embed:
            save_dir = os.path.join(self.save_dir, 'embed_' + self.name)
            with open(os.path.join(save_dir, 'config.json')) as f:
                js = json.load(f)
            self.chars = js['chars']
        else:
            self.chars = [C0] + list(set([w for point in data for w in point]))
        self.vocab = dict(zip(self.chars, range(len(self.chars))))
        self.vocab_size = len(self.vocab)


