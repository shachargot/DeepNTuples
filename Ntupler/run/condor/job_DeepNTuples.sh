#!/bin/bash
pythonFilename=$1
processID=$2
MiniAODFile=$3

set --  # This clears $1, $2, etc.

export HOME=$(pwd)

# Step 1: Create a job-specific config with modified input/output
jobConfig="DeepNTuplizerAK8Scout${processID}.py"
cp $pythonFilename $jobConfig

echo "Modifying config to use:"
echo "  Input:  ${MiniAODFile}"
echo "  Output: ${OutputFile:-<using default from config>}"

# Step 2: run cmsRun
echo "Doing cmsRun for DeepNTuples."
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsenv
cmsRun $jobConfig inputFiles=${MiniAODFile}

exitCode=$?
if [ $exitCode -ne 0 ]; then
    echo "ERROR: cmsRun (1st step) failed with exit code $exitCode"
    exit $exitCode
fi

rm $jobConfig

echo "Job completed successfully."
