# DNNTuplesAK8

## Setup
```bash
git cms-addpkg PhysicsTools/ONNXRuntime
git clone https://github.com/colizz/DNNTuples.git DeepNTuples -b dev-nanov15
$CMSSW_BASE/src/DeepNTuples/Ntupler/scripts/install_onnxruntime.sh  # Is this needed?

# If onnxruntime is not up to date
cp /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/cmssw/CMSSW_15_0_4/config/toolbox/el9_amd64_gcc12/tools/selected/onnxruntime.xml $CMSSW_BASE/ORT_INSTALL/onnxruntime.xml 
scram setup $CMSSW_BASE/ORT_INSTALL/onnxruntime.xml

scram b -j 8

cd Ntupler/test
cmsRun DeepNtuplizerAK8Scout.py
```

## Some documentation:

### DeepNtuplizer

`NTupler/test/DeepNtuplizerAK8Scout.py`: 
* Makes ScoutingFatPFJetsReclustered                         (minPt changed to 25.0, any other custom changes needed?)
* Scouting jets matched to offline fat slimmedJetsAK8      (Do offline jets have pt cut by default that we need to change?)
* Offline fat jets gen-matched to ak8GenJetsWithNu/ak8GenJetsWithNoNu    (AK8GenJets with/without neutrinos - I don't think we need this distinction)
* Calls `NTupler/plugins/DeepNtuplizer.cc` with config `NTupler/python/DeepNtuplizer_cfi.py`

`NTupler/plugins/DeepNTuplizer.cc`:
* Creates modules for Jets, FatJets, ScoutingJets, SVs, and PFCands
* Calls all modules on each "Uncorrected" offline fatjet in each event


`NTupler/python/DeepNtuplizer\_cfi.py`:
* jetMinPt changed to 25.0       (Any other changes needed?)
* Uses ParticleNet-MD tagger by default  

### Modules 
All operate on `slimmedJetsAK8`. Definitions found in `Ntupler/src`
 
`JetInfoFiller`: 
* Gets jet flavor (definition in `/BTagHelpers/src/FlavorDefinition.cc`)

**Note**:  `usePhysForLightAndUndefined` variable changed to `true` to allow gluon jets 

`FatJetInfoFiller`: 
* Gen-matches jet to particle by pdgId, then fills all kinematics 
* New upsiloni\_label created in `/FatJetHelpers/src/FatJetMatching.cc` (Currently only Upsilon->3g implemented!) 

**Note**: QCD labels are currently default: bb, b, cc, c, others. May need to change later. 

`ScoutingFatJetCompleteFiller`: 
* Same as `FatJetInfoFiller` for scouting fatjets.


<!-- 
## Submit jobs via CRAB

**Step 0**: switch to the crab production directory and set up grid proxy, CRAB environment, etc.

```bash
cd $CMSSW_BASE/src/DeepNTuples/Ntupler/run
# set up grid proxy
voms-proxy-init -rfc -voms cms --valid 168:00
# set up CRAB env (must be done after cmsenv)
source /cvmfs/cms.cern.ch/common/crab-setup.sh
```

**Step 1**: use the `crab.py` script to submit the CRAB jobs:

`python crab.py --set-input-dataset -p ../test/DeepNtuplizerAK8.py --site T2_CH_CERN -o /store/user/$USER/DeepNtuples/[version] -t DeepNtuplesAK8-[version] --no-publication -i [ABC].conf -s FileBased -n 5 --work-area crab_projects_[ABC] --send-external [--input_files JEC.db] --dryrun`

These command will perform a "dryrun" to print out the CRAB configuration files. Please check everything is correct (e.g., the output path, version number, requested number of cores, etc.) before submitting the actual jobs. To actually submit the jobs to CRAB, just remove the `--dryrun` option at the end.

**[Note] For the QCD samples use `-n 1 --max-units 20` to run one file per job, and limit the total files per job to 20.**


**Step 2**: check job status

The status of the CRAB jobs can be checked with:

```bash
./crab.py --status --work-area crab_projects_[ABC]
```

Note that this will also resubmit failed jobs automatically.

The crab dashboard can also be used to get a quick overview of the job status:
`https://dashb-cms-job.cern.ch/dashboard/templates/task-analysis`

More options of this `crab.py` script can be found with:

```bash
./crab.py -h
``` -->
