import os
import re
import tempfile
import subprocess
import json

from nmtwizard.utility import Utility
from nmtwizard.logger import get_logger

LOGGER = get_logger(__name__)

class ScoreUtility(Utility):

    def __init__(self):
        super(ScoreUtility, self).__init__()
        self._tools_dir = os.getenv('TOOLS_DIR', '/root/tools')

    @property
    def name(self):
        return "score"

    def declare_arguments(self, parser):
        subparsers = parser.add_subparsers(help='Run type', dest='cmd')
        parser_score = subparsers.add_parser('score', help='Evaluate translation.')
        parser_score.add_argument('-o', '--output', required=True, nargs='+',
                                  help='Output file from translation.')
        parser_score.add_argument('-r', '--ref', required=True, nargs='+',
                                  help='Reference file.')
        parser_score.add_argument('-f', '--file', default='-',
                                  help='file to save score result to.')
        parser_score.add_argument('-l', '--lang', default='en',
                                  help='Lang ID')

    def convert_to_local_file(self, nextval):
        new_val = []
        for val in nextval:
            inputs = val.split(',')
            local_inputs = []
            for remote_input in inputs:
                local_input = os.path.join(self._data_dir, self._storage.split(remote_input)[-1])
                self._storage.get_file(remote_input, local_input)
                local_inputs.append(local_input)
            new_val.append(','.join(local_inputs))
        return new_val

    def eval_BLEU(self, tgtfile, reffile):
        reffile = reffile.replace(',', ' ')
        result = subprocess.check_output('perl %s %s < %s' % (
                                            os.path.join(self._tools_dir, 'BLEU', 'multi-bleu-detok_cjk.perl'),
                                            reffile,
                                            tgtfile), shell=True)  # nosec
        bleu = re.match(r"^BLEU\s=\s([\d\.]+),", result.decode('ascii'))
        return bleu.group(1)

    def exec_function(self, args):
        list_output = self.convert_to_local_file(args.output)
        list_ref = self.convert_to_local_file(args.ref)

        if len(list_output) != len(list_ref):
            raise ValueError("`--output` and `--ref` should have same number of parameters")

        score = {}
        for i, output in enumerate(list_output):
            score[args.output[i]] = {}
            score[tgt_base]['BLEU'] = self.eval_BLEU(output, list_ref[i])

        # dump score to stdout, or transfer to storage as specified
        if args.file == '-':
            print(json.dumps(score))
        else:
            with tempfile.NamedTemporaryFile() as file_handler:
                file_handler.write(json.dumps(score))
                file_handler.flush()
                self._storage.push(file_handler.name, args.file)


if __name__ == '__main__':
    ScoreUtility().run()