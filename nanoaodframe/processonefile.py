#!/bin/python
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 14 11:01:46 2018

@author: Suyong Choi (Department of Physics, Korea University suyong@korea.ac.kr)
@refactored for LFV analysis: Jiwon Park (jiwon.park@cern.ch)

This script applies nanoaod processing to one file
"""
import sys, os, re, argparse
import cppyy
import ROOT

if __name__=='__main__':

    parser = argparse.ArgumentParser(usage="%prog [options]")
    parser.add_argument("-I", "--infile",  dest="infile", type=str, default="", help="Input file name")
    parser.add_argument("-O", "--outputroot", dest="outputroot", type=str, default="", help="Output file in your working directory")
    parser.add_argument("-Y", "--year", dest="year", type=str, default="", help="Select 2016pre, 2016post, 2017, or 2018 runs")
    parser.add_argument("-S", "--syst", dest="syst", type=str, default="theory", help="Systematic: 'data' for Data, 'nosyst' for mc without uncertainties. Default is 'theory'. To run without theory unc for TT samples, put 'all'.")
    parser.add_argument("-D", "--dataset", dest="dataset", action="store", nargs="+", default=[], help="Put dataset folder name (eg. TTTo2L2Nu) to process specific one.")
    parser.add_argument("-F", "--dataOrMC", dest="dataOrMC", type=str, default="", help="data or mc flag, if you want to process data-only or mc-only")
    options = parser.parse_args()

    outputroot = options.outputroot
    infile = options.infile
    year = options.year
    syst = options.syst

    json = ""
    if 'data' in indir[5:]:
        if syst == "data":
            if "2016" in indir:
                json = os.path.join(workdir, "data/GoldenJSON/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt")
            elif "2017" in indir:
                json = os.path.join(workdir, "data/GoldenJSON/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt")
            elif "2018" in indir:
                json = os.path.join(workdir, "data/GoldenJSON/Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt")

    print("Input: " + indfile + ", " + "Output: " + outputroot + ", Syst: " + syst + ", Json: " + json + "\n")

    if not re.match('.*\.root', outputroot):
        print("Output file should be a root file! Quitting")
        exit(-1)

    # load compiled C++ library into ROOT/python
    cppyy.load_reflection_info("libnanoadrdframe.so")
    t = ROOT.TChain("Events")
    tmpf = ROOT.TFile.Open(infile)
    tmpt = tmpf.Get("Events")
    if tmpt.GetEntries() > 0:
        t.Add(infile)
    aproc = aproc = ROOT.TopLFVAnalyzer(t, outputroot, year, syst, json, "", 1)
    aproc.setupAnalysis()
    aproc.run(False, "Events")

    # process input rootfiles to sum up all the counterhistograms
    counterhistogramsum = None
    intf = ROOT.TFile(infile)
    counterhistogram = intf.Get("hcounter")
    counterhistogramsum = counterhistogram.Clone()
    counterhistogramsum.SetDirectory(0)
    intf.Close()

    if counterhistogramsum != None:
        print("Updating with counter histogram")
        outf = ROOT.TFile(outputroot, "UPDATE")
        counterhistogramsum.Write()
        outf.Write("", ROOT.TObject.kOverwrite)
        outf.Close()
    else:
        print("counter histogram not found")
