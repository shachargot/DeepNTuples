#!/cvmfs/sft.cern.ch/lcg/views/LCG_108/x86_64-el9-clang19-opt/bin/python

import sys,os,pathlib,re
import argparse as ap
import subprocess as sub
from util.condor.utils import CondorRunner
from util.args.args import FileListAction

class DeepNTuplesCondorRunner(CondorRunner):
    # NOTE: This is almost identical to MiniAODCondorRunner.
    def __init__(self):
        super().__init__()
        self.needs_args_file = True

    def write_args_file(self, args):
        arguments_file = '{}/arguments.txt'.format(args['runDirectory'])

        # DeepNTuples executable 
        cmssw_base = os.environ.get('CMSSW_BASE')
        config_file = f"{cmssw_base}/src/DeepNTuples/Ntupler/test/DeepNtuplizerAK8Scout.py"

        with open(arguments_file,'w') as f:
            for i,file in enumerate(args['MINIAOD']):
                basename = pathlib.Path(file).name
                if(args['BRUX']):
                    arguments = '{} {} {} {}'.format(config_file,i,f'file:{file}','UNUSED')
                else:
                    arguments = '{} {} {} {}'.format(config_file,i,basename,file)
                f.write(arguments + '\n')
        return

    def copy_config_files(self, args):
        """
        Overloading this function, so that we can modify
        the number of output events from the ScoutingNANO job.
        e.g. useful when running on large QCD samples and we
        don't actually want the full set of events.
        """

        if('nEvents' in args.keys()):
            # We will copy over the configuration file, but modify the number of events
            # in the output line.
            trigger_phrase = 'output = cms.untracked.int32'
            for key in args.keys():
                if('inputFile' in key):

                    with open(args[key],'r') as f:
                        lines = f.readlines()

                    for i in range(len(lines)):
                        if(trigger_phrase in lines[i]):
                            lines[i] = f'    {trigger_phrase}({int(args["nEvents"])})\n'

                    new_filename = f'{args["runDirectory"]}/{args[key].split("/")[-1]}'
                    with open(new_filename,'w') as f:
                        for line in lines:
                            f.write(line)
        else:
            super().copy_config_files(args)
        return

    def copy_customization_dir(self, args):
        """
        Copy the entire customizations directory into the run directory,
        one level above all job*/ subdirectories. The shell script will
        then copy its contents into the CMSSW src area at runtime.

        Does nothing if no customization directory was specified or if
        no customization is being applied.
        """
        # In fill_condor_template, replacing the single-string handling:
        customize = args.get('customize', []) or []
        if isinstance(customize, str):
            customize = [customize] if customize else []
        customize = ' '.join(customize)  # space-separated list

        customize_dir = args.get('customizeDir', None)

        if not customize:
            return  # nothing to do

        if customize_dir is None:
            # Default: look for a 'customizations/' directory next to this script
            #TODO: Explicitly define this dir in main, before adding corresponding arg?
            this_dir = str(pathlib.Path(__file__).resolve().parent)
            customize_dir = str(pathlib.Path(this_dir) / 'customizations')

        customize_dir = str(pathlib.Path(customize_dir).resolve())

        if not pathlib.Path(customize_dir).exists():
            raise FileNotFoundError(
                f'Customisation directory not found: {customize_dir}\n'
                f'Please create it or pass --customizeDir explicitly.'
            )

        dest = str(pathlib.Path(args['runDirectory']) / 'customizations')
        sub.check_call(['cp', '-r', customize_dir, dest])
        # print(f'Copied customization directory: {customize_dir} -> {dest}')
        return

    def fill_condor_template(self, args):
        super().fill_condor_template(args)

        # The customize argument is constant across all jobs in this batch,
        # so we bake it directly into the submission file rather than arguments.txt.
        # An empty string is passed when no customization is requested; the shell
        # script checks for this and skips the --customize flag accordingly.
        # In fill_condor_template, replacing the single-string handling:
        customize = args.get('customize', []) or []
        if isinstance(customize, str):
            customize = [customize] if customize else []
        customize_arg = ' '.join(customize)  # space-separated list

        for i,line in enumerate(self.condor_submit_lines):
            self.condor_submit_lines[i] = self.condor_submit_lines[i].replace("$CUSTOMISE_ARG", customize_arg)
            self.condor_submit_lines[i] = self.condor_submit_lines[i].replace("$MEMORY", args['memory'])

            # Remove the transfer_inputs line for BRUX usage, it's unused there anyway.
            if(args['BRUX']):
                if('transfer_input_files' in self.condor_submit_lines[i]):
                    self.condor_submit_lines[i] = ''

    def prepare_run_directory(self, args, this_dir=None):
        result = super().prepare_run_directory(args, this_dir)
        if result:
            self.copy_customization_dir(args)
        return result

def natural_sort_key(filepath):
    # Convert to string if Path object
    s = str(filepath)

    # Split into text and number parts
    # \d+ matches one or more digits
    parts = re.split(r'(\d+)', s)

    # Convert numeric parts to integers, leave text as-is
    return [int(part) if part.isdigit() else part.lower() for part in parts]

def sort_job_files(filepaths):
    return sorted(filepaths, key=natural_sort_key)

def launch_jobs(condor_submission_file, args):
    condor_filename = condor_submission_file.split('/')[-1]
    command = ['condor_submit',condor_filename]
    sub.check_call(command,cwd=args['runDirectory'])
    return

def main(args):
    parser = ap.ArgumentParser()
    parser.add_argument('-miniaod','--MINIAOD',action=FileListAction,nargs='+',required=True,
                        help='MiniAOD ROOT file inputs. Can be list of filenames, glob-compatible string, or delimited string.')
    parser.add_argument('-r','--runDirectory',type=str,default='condorjobs',
                        help='Directory where jobs are produced and run from.')
    parser.add_argument('-f','--force',action='store_true')
    parser.add_argument('-b','--batchName',type=str,default=None,
                        help='Condor batch name.')
    parser.add_argument('-nCPU','--nCPU',type=int,default=1,
                        help='Number of CPUs per job.')
    parser.add_argument('-memory','--memory',type=str,default='2GB',
                        help='Memory string for condor job (default is "2GB").')
    parser.add_argument('-BRUX','--BRUX',type=int,default=1,
                        help='If using BRUX, where condor acts weirdly.')
    parser.add_argument('-run','--run',action='store_true',
                        help='Launch resulting condor jobs immediately.')
    parser.add_argument('-debug','--debug',action='store_true',
                        help='Prepare single job.')
    parser.add_argument('-nEvents','--nEvents',type=int,default=-1,
                        help='Number of output events. If <0 (default), matches number of input events from MiniAOD.')
    parser.add_argument('--customize', type=str, default='', nargs='*',
                        help=(
                            'One or more customisation functions to append to the config, '
                            'as module.function pairs, e.g. '
                            'customize_upsilon_cff.addUpsilonGenTable '
                            'customize_subjets_cff.addSubjetTables. '
                            'Each is appended to the config in order.'
                        ))
    parser.add_argument('-customizeDir','--customizeDir',type=str,default=None,
                        help=(
                            'Path to directory containing customization Python modules & plugins. '
                            'This entire directory will be copied into the run directory and then '
                            'into the CMSSW src area by the job script. '
                            'Defaults to a "customizations/" subdirectory next to this script.'
                        ))

    args = vars(parser.parse_args())
    args['BRUX'] = args['BRUX'] > 0

    # Normalise: treat nEvents < 0 as "not set" so copy_config_files behaves correctly
    if args['nEvents'] < 0:
        del args['nEvents']

    args['MINIAOD'] = sort_job_files(args['MINIAOD'])

    if(args['debug']):
        args['MINIAOD'] = [args['MINIAOD'][0]]

    for i,line in enumerate(args['MINIAOD']):
        if('root://' not in line):
            args['MINIAOD'][i] = str(pathlib.Path(line).absolute())

    # CondorRunner expects an nJobs entry in args
    args['nJobs'] = len(args['MINIAOD'])

    this_dir = str(pathlib.Path(__file__).resolve().parent) # not thrown off by symlinks

    runner = DeepNTuplesCondorRunner()
    runner.set_jobname('job_DeepNTuples.sh')

    # Prepare the run directory (also copies customizations/ if needed).
    result = runner.prepare_run_directory(args,this_dir)
    if(not result):
        return

    # Prepare the condor submission file.
    condor_submission_template = str(pathlib.Path('{}/templates/condor_DeepNTuples.sub'.format(this_dir)).absolute())
    condor_submission_file = runner.create_condor_submission_file(condor_submission_template,args)

    if(args['run']):
        launch_jobs(condor_submission_file,args)

    print('Done')

if(__name__=="__main__"):
    main(sys.argv)
