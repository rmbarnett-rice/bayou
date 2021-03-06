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

import argparse
import os
import ast
import pickle

from model import Model

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--save_dir', type=str, default='save',
                       help='model directory to laod from')
    parser.add_argument('--topic', type=str, required=True,
                       help='input topic vector')
    parser.add_argument('--topk', type=int, default=5,
                       help='print top-k values in distribution')
    parser.add_argument('--prime', default='[("DBlock", "V")]',
                       help='prime path')

    args = parser.parse_args()
    predict(args)

def predict(args):
    with open(os.path.join(args.save_dir, 'config.pkl'), 'rb') as f:
        saved_args = pickle.load(f)
    with open(os.path.join(args.save_dir, 'chars_vocab.pkl'), 'rb') as f:
        chars, vocab = pickle.load(f)
    model = Model(saved_args, True)
    topic = ast.literal_eval(args.topic)
    with tf.Session() as sess:
        tf.global_variables_initializer().run()
        saver = tf.train.Saver(tf.global_variables())
        ckpt = tf.train.get_checkpoint_state(args.save_dir)
        if ckpt and ckpt.model_checkpoint_path:
            saver.restore(sess, ckpt.model_checkpoint_path)
            dist, prediction = model.predict(sess, ast.literal_eval(args.prime), topic, chars, vocab)
            dist = [(chars[i], prob) for i, prob in enumerate(dist)]

            for node, prob in sorted(dist, key=lambda x:x[1], reverse=True)[:args.topk]:
                print('{:.2f} : {}'.format(prob, node))
            print('prediction : {}'.format(prediction))

if __name__ == '__main__':
    main()
