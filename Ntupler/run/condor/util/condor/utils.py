import sys,os,pathlib
import argparse as ap
import subprocess as sub

class CondorRunner:

    def __init__(self):
        self.jobname = None
        self.jobdirs = []
        self.condor_submit_lines = []
        self.needs_args_file = False # certain jobs will write an arguments file for HTCondor, others won't

    def set_jobname(self,val:str):
        self.jobname = val

    def fetch_requirements(self,entries=None,require_cvmfs=False, blacklist_file=None):
        requirements = []
        if(entries is not None):
            if(isinstance(entries,str)):
                requirements += entries.split(' ')
            else:
                requirements += entries

        blacklist = []
        if(blacklist_file is not None):
            with open(blacklist_file,'r') as f:
                blacklist= f.readlines()
        blacklist = [x.strip().strip('\n') for x in blacklist]

        if(require_cvmfs):
            requirements.append("HAS_CVMFS =?= TRUE")
        requirements += ["machine != \"{}\"".format(x) for x in blacklist]

        if(len(requirements) > 0):
            requirements = "(" + " && ".join(requirements) + ")"
        else:
            requirements = ""
        return requirements

    def copy_config_files(self,args):
        for key in args.keys():
            if('inputFile' in key):
                command = ['cp',args[key],args['runDirectory']]
                sub.check_call(command)
        return

    def prepare_run_directory(self,args,this_dir=None):
        if(this_dir is None):
            print('Warning: No argument passed for "this_dir". Default might not work.')
            this_dir = str(pathlib.Path(str(pathlib.Path(__file__).resolve().parent) + '/../..').resolve())

        # Create the run directory.
        if(pathlib.Path(args['runDirectory']).exists() and not args['force']):
            print('Error: run directory {} exists already.'.format(args['runDirectory']))
            return False
        elif(pathlib.Path(args['runDirectory']).exists()): # force
            sub.check_call(['rm','-r',args['runDirectory']])
        os.makedirs(args['runDirectory'])

        # Copy the job script to the run directory
        job_script = '{}/{}'.format(this_dir,self.jobname)
        command = ['cp',job_script,args['runDirectory']]
        sub.check_call(command)

        # Copy the input Python file(s) to the run directory.
        self.copy_config_files(args)

        # Copy the setup script to the run directory
        # setup_script = '{}/setup/cmssw_setup.sh'.format(this_dir)
        # command = ['cp',setup_script,args['runDirectory']]
        # sub.check_call(command)

        # Create the subdirectories for all the jobs in the rundir.
        self.jobdirs = []
        for i in range(args['nJobs']):
            subdir = '{}/job{}'.format(args['runDirectory'],i)
            os.makedirs(subdir)
            self.jobdirs.append(subdir)

        # Some types of jobs require and arguments file.
        # (Check whatever template HTCondor submission file is being used!)
        if(self.needs_args_file):
            self.write_args_file(args)
        return True

    def write_args_file(self,args):
        print('You need to implement this!')
        assert False

    def get_condor_template(self,path):
        with open(path,'r') as f:
            self.condor_submit_lines = f.readlines()
        return

    def fill_condor_template(self,args):
        batch_line = 'batch_name = {}'
        if(args['batchName'] is not None): batch_line = batch_line.format(args['batchName'])
        else: batch_line = '#' + batch_line

        requirements_string = self.fetch_requirements(None,blacklist_file=None)
        if(requirements_string is not None):
            if(len(requirements_string) > 0):
                requirements_string = 'requirements            = {}'.format(requirements_string)

        try:
            config_file = '../' + args['inputFile'].split('/')[-1] # remove any leading directory; this file has been copied appropriately
        except:
            config_file = ''

        for i,line in enumerate(self.condor_submit_lines):
            self.condor_submit_lines[i] = self.condor_submit_lines[i].replace("$BATCH_NAME",batch_line + '\n')
            self.condor_submit_lines[i] = self.condor_submit_lines[i].replace("$NJOBS",str(args['nJobs']))
            self.condor_submit_lines[i] = self.condor_submit_lines[i].replace("$N_CPU",str(args['nCPU']))
            self.condor_submit_lines[i] = self.condor_submit_lines[i].replace('$REQUIREMENTS',requirements_string)
            self.condor_submit_lines[i] = self.condor_submit_lines[i].replace("$CONFIG_FILE",config_file)
            try:
                self.condor_submit_lines[i] = self.condor_submit_lines[i].replace("$SETUP_SCRIPT",'../cmssw_setup.sh') # will have been copied to run directory, which is one up from initialdir
                self.condor_submit_lines[i] = self.condor_submit_lines[i].replace("$SEED_OFFSET",str(args['seedOffset']))
            except:
                pass

            # Remove the transfer_inputs line for BRUX usage, it's unused there anyway.
            if(args['BRUX']):
                if('transfer_input_files' in self.condor_submit_lines[i]):
                    self.condor_submit_lines[i] = ''

    def create_condor_submission_file(self,condor_submission_template,args):
        self.get_condor_template(condor_submission_template)

        self.fill_condor_template(args)

        condor_filename = condor_submission_template.split('/')[-1]
        condor_submission_file = '{}/{}'.format(args['runDirectory'],condor_filename)
        with open(condor_submission_file,'w') as f:
            for line in self.condor_submit_lines:
                f.write(line)
        return condor_submission_file
