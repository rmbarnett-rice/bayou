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
from tensorflow.python.ops import seq2seq

import decoder
from utils import weighted_pick
from cells import TopicRNNCell, TopicLSTMCell
from data_reader import CHILD_EDGE, SIBLING_EDGE
import numpy as np

class Model():
    def __init__(self, args, infer=False):
        self.args = args
        if infer:
            args.batch_size = 1
            args.seq_length = 1

        cell = TopicLSTMCell if args.cell == 'lstm' else TopicRNNCell
        self.cell1 = cell(args.rnn_size)
        self.cell2 = cell(args.rnn_size)

        self.node_data = [tf.placeholder(tf.int32, [args.batch_size], name='node{0}'.format(i))
                for i in range(args.seq_length)]
        self.edge_data = [tf.placeholder(tf.bool, [args.batch_size], name='edge{0}'.format(i))
                for i in range(args.seq_length)]
        self.topic_data = [tf.placeholder(tf.float32, [args.batch_size, args.ntopics], name='topic{0}'.format(i))
                for i in range(args.seq_length)]
        self.targets = tf.placeholder(tf.int32, [args.batch_size, args.seq_length])
        self.initial_state = self.cell1.zero_state(args.batch_size, tf.float32)

        projection_w = tf.get_variable("projection_w", [args.rnn_size, args.vocab_size])
        projection_b = tf.get_variable("projection_b", [args.vocab_size])

        outputs, last_state = decoder.embedding_rnn_decoder(self.node_data, self.edge_data, self.topic_data, self.initial_state, self.cell1, self.cell2, args.vocab_size, args.rnn_size, (projection_w,projection_b), feed_previous=infer)
        output = tf.reshape(tf.concat(1, outputs), [-1, args.rnn_size])
        self.logits = tf.matmul(output, projection_w) + projection_b
        self.probs = tf.nn.softmax(self.logits)
        self.cost = seq2seq.sequence_loss([self.logits],
                [tf.reshape(self.targets, [-1])],
                [tf.ones([args.batch_size * args.seq_length])])
        self.final_state = last_state
        self.train_op = tf.train.AdamOptimizer(args.learning_rate).minimize(self.cost)

        var_params = [np.prod([dim.value for dim in var.get_shape()]) for var in tf.trainable_variables()]
        if not infer:
            print('Model parameters: {}'.format(np.sum(var_params)))

    def predict(self, sess, prime, topic, chars, vocab):

        state = self.cell1.zero_state(1, tf.float32).eval()
        t = np.array(np.reshape(topic, (1, -1)), dtype=np.float)
        for node, edge in prime:
            assert edge == CHILD_EDGE or edge == SIBLING_EDGE, 'invalid edge: {}'.format(edge)
            node_data, edge_data = np.zeros((1,), dtype=np.int32), np.zeros((1,), dtype=np.int32)
            node_data[0] = vocab[node]
            edge_data[0] = edge == CHILD_EDGE

            feed = {self.initial_state: state,
                    self.node_data[0].name: node_data,
                    self.edge_data[0].name: edge_data,
                    self.topic_data[0].name: t}
            [probs, state] = sess.run([self.probs, self.final_state], feed)

        dist = probs[0]
        prediction = chars[weighted_pick(dist)]
        return dist, prediction
