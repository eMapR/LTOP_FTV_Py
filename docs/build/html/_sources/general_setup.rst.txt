This document outlines the overall workflow for running a version of LTOP that is (mostly) based on five GEE steps. Note that this version of the algorithm and the associated documentation has been updated to run in the GEE Python API and requires less input from the user than the original implementation. This is still a work in progress and will likely evolve in future versions. The way this is set up currently, you will run a Python script which will execute (almost) all of the steps in the workflow. It will generate intermediate outputs to a GEE assets directory of your choosing. Most of the steps are set up to 'wait' for the previous step to finish before initiating. 

The workflow assumes some understanding of running scripts in GEE, generating jobs and exporting 
assets or files to gDrive. The approach also assumes some understanding of Python and how to at 
least run a Python script in an IDE or from the command line. We start by outlining some of the 
background for the process, some information on the general overview of the workflow and how this 
could be set up for somebody to actually run. We then go through the steps to produce LTOP output,
 how the outputs can be assessed and then some of the pitfalls one might run into while carrying 
 out this workflow. Note that to produce temporally stabilized outputs of an existing time series 
 see the SERVIR_stabilization [GitHub repository](https://github.com/eMapR/SERVIR_stabilization). 

`General overview of theory and background <https://docs.google.com/presentation/d/1ra8y7F6_vyresNPbT3kYamVPyxWSfzAm7hCMc6w8N-M/edit?usp=sharing>`

Workflow conceptual diagram: 
.. image:: `<https://docs.google.com/drawings/d/e/2PACX-1vQ9Jmb4AhD86GedXTH798O4hGCNDyCp-ZMcYEB1Ij8fuhNqc4xhDuO3x9JSttq6Tk2g9agWP2FWhoU-/pub?w=960&h=720>`
