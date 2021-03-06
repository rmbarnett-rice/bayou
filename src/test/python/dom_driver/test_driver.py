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
import os
import json
import subprocess

# list of tests that use the Android API
android = [ '27f' ]

testdir = '../test/pl/driver'
outdir = '../src/pl/out/artifacts/driver'
passed = 0
failed = 0

class bcolors:
    OK = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def printOK(p):
    global passed
    print(bcolors.OK + '[OK]' + bcolors.ENDC + p, end='')
    passed += 1

def printFAIL(p):
    global failed
    print(bcolors.FAIL + '[FAIL]' + bcolors.ENDC + p, end='')
    failed += 1

for f in os.listdir('../test/pl/driver'):
    if not f.endswith('.java'):
        continue
    c = 'config2.json' if f[:-5] in android else 'config1.json'
    with open(os.path.join(testdir, f)) as fp:
        content = fp.readline()[2:]
    try:
        process = subprocess.run(['java',
                      '-jar', os.path.join(outdir, 'driver.jar'),
                      '-f', os.path.join(testdir, f),
                      '-c', os.path.join(testdir, c)],
                  stdout=subprocess.PIPE, check=True)
        output = process.stdout.decode('utf-8')
        o = os.path.join(testdir, f[:-6] + 'o.json')
        if os.path.getsize(o) == 0: # empty output expected
            assert output == ''

        # compare ASTs and evidences in JSON
        js = json.loads('{"programs": [' + output + ']}')
        with open(o) as fp:
            jso = json.loads('{"programs": [' + fp.read() + ']}')
        assert len(jso['programs']) == len(js['programs'])
        for expected, out in zip(jso['programs'], js['programs']):
            assert all([expected['ast'] == out['ast']])
            assert len(expected['sequences']) == len(out['sequences'])
            assert all([set(expected['keywords']) == set(out['keywords'])])
            assert all([expected['javadoc'] == out['javadoc']])
        printOK(content)
    except (subprocess.CalledProcessError, AssertionError) as _:
        printFAIL(content)

print('{}/{} tests passed, {} failed'.format(passed, passed+failed, failed))

