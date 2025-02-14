import os, sys, glob, re
import ROOT
from ROOT import *
import numpy as np
import subprocess

input = sys.argv[1]
year = sys.argv[2]
if year not in ['2016pre', '2016post', '2017', '2018']:
    print('Wrong year, check again')
    sys.exit()
forceHadd = False
if len(sys.argv) > 3: forceHadd = sys.argv[3] == "True"
if forceHadd: print("Hadd all split MC!!")

yield_name = 'h_ncleanjetspass'
base_path = './'
nom_path = os.path.join(base_path, input, year)
if not os.path.exists(nom_path):
    print("Folder '{}' does not exists.".format(nom_path))
    sys.exit()
else:
    print("Start postprocessing at '{}'.".format(nom_path))

isFFcalc = False
isFFapply = False
if 'fake' in input: isFFcalc = True
elif 'FF' in input: isFFapply = True

# Set output folders
out_path = os.path.join(base_path, input, year + '_postprocess')
fig_path = os.path.join(base_path, input, 'figure_' + year)
if not os.path.exists(out_path):
    os.makedirs(out_path)
if not os.path.exists(fig_path):
    os.makedirs(fig_path)
if not os.path.exists(os.path.join(fig_path, 'qcd')):
    os.makedirs(os.path.join(fig_path, 'qcd'))
if not os.path.exists(os.path.join(fig_path, 'dyincl')):
    os.makedirs(os.path.join(fig_path, 'dyincl'))
if not os.path.exists(os.path.join(fig_path, 'dyincl', 'qcd')):
    os.makedirs(os.path.join(fig_path, 'dyincl', 'qcd'))

file_list = [i.replace('.root', '') for i in os.listdir(nom_path) if '.root' in i]
data_list = [i[:i.find('201')] for i in os.listdir(nom_path) if '.root' in i and '201' in i and 'jes' not in i]
data_list = list(set(data_list))
split_list = []
try:
    split_list = [re.sub(r'_[0-9]*.root', '', i) for i in os.listdir(os.path.join(nom_path, 'split')) if '.root' in i]
except: pass
split_list = list(set(split_list))
#print(data_list)
#print(file_list)
#print(split_list)

def get_bSFratio(inputf, inputh):
    # ref: https://twiki.cern.ch/twiki/bin/viewauth/CMS/BTagShapeCalibration
    # rescale histogram by Sum(event weights before applying b weight)/Sum(weights with b weight)
    # This should be done per jet bin - nojet / 3jet

    step = inputh[inputh.rfind('_S')+1:inputh.rfind('_S')+3]

    # This depends on cutflow
    if int(step[-1]) < 4: step = 'S' + step[-1]
    else                : step = 'S4'

    if isFFcalc: step = 'S2'

    posthist = inputf.Get('h_nevents_' + step)
    prehist = inputf.Get('h_nevents_' + step + '_nobtag')
    if '__btag' in inputh:
        posthist = inputf.Get('h_nevents_' + step + '__' + str(inputh.split('__')[-1]))
    if prehist.Integral() * posthist.Integral() == 0:
        return 1.0
    #print(prehist.Integral() / posthist.Integral())
    return prehist.Integral(0, prehist.GetNbinsX()+1) / posthist.Integral(0, prehist.GetNbinsX()+1)


def rescale(inputh, inputf, bsff, sumW, nom_sumW): # rescale up/dn histos

    #Only for ext syst. such as tune and hdamp, not jes/jer/tes
    h = inputf.Get(inputh)
    if not any(i in inputh for i in ['event', 'counter', '_nobtag', 'LHEPdfWeightSum', 'PSWeightSum', 'ScaleWeightSum']):
        h.Scale(get_bSFratio(bsff, inputh))
        h.Scale(nom_sumW.GetBinContent(2) / sumW.GetBinContent(2))
        #h.Rebin(nrebin)
        #h = h.Rebin(len(rebin[h.GetName().split('_')[2]])-1, h.GetName(), array.array('d',rebin[h.GetName().split('_')[2]]))
        if yield_name in inputh:
            h1 = h.Clone('h1')
            h1.SetName(inputh.replace(yield_name, yield_name + '_yield'))
            outfile.cd()
            h1.Write()

    outfile.cd()
    h.Write()


def write_envelope(inputh, inputf, bsff, syst, nhists, gen_sumW, wgt_sumW):

    #I didn't want this way...later, fill weight name in hist bins, and FindBin to get the bin
    #bin num for up/dn sum weights, branch idx + 1
    sum_weights_dict = {
        "mescale": [9, 1],
        "renscale": [8, 2],
        "facscale": [6, 4],
        "isr": [1, 3],
        "fsr": [2, 4],
        "pdfalphas": [103, 102],
    }

    if nhists == 2: #up/dn, only re-normalization
        up = inputf.Get(inputh + "__" + syst + "up")
        dn = inputf.Get(inputh + "__" + syst + "down")
        if up == None: return 1
        up.SetDirectory(ROOT.nullptr)
        dn.SetDirectory(ROOT.nullptr)
        #print("gen_sumW.GetBinContent(2)", gen_sumW.GetBinContent(2))
        #Zero sum weight means no variation, especially for alphas
        if wgt_sumW.GetBinContent(sum_weights_dict[syst][0]) * wgt_sumW.GetBinContent(sum_weights_dict[syst][1]) > 0:
            up.Scale(gen_sumW.GetBinContent(2)/wgt_sumW.GetBinContent(sum_weights_dict[syst][0]))
            dn.Scale(gen_sumW.GetBinContent(2)/wgt_sumW.GetBinContent(sum_weights_dict[syst][1]))
            up.Scale(get_bSFratio(bsff, up.GetName()))
            dn.Scale(get_bSFratio(bsff, dn.GetName()))
        up.SetName(inputh + "__" + syst + "up")
        dn.SetName(inputh + "__" + syst + "down")

        up.Write()
        dn.Write()

        if yield_name in inputh:
            up_yield = up.Clone('up_yield')
            dn_yield = dn.Clone('dn_yield')
            up_yield.SetName(inputh.replace(yield_name, yield_name + '_yield') + "__" + syst + "up")
            dn_yield.SetName(inputh.replace(yield_name, yield_name + '_yield') + "__" + syst + "down")
            up_yield.Write()
            dn_yield.Write()


    elif (inputh + "__" + syst + "0")  in hlists:
        var_list = []
        for x in range(0,nhists):
            h = inputf.Get(inputh + "__" + syst + str(x))
            if any(x in syst for x in ['scale']):
                pass
            #elif 'pdf' in syst:
            #  if x == 0: continue
            #  h.Scale(gen_sumW.GetBinContent(2) / wgt_sumW.GetBinContent(1))
            else: h.Scale(gen_sumW.GetBinContent(2) / wgt_sumW.GetBinContent(x+1))
            #h.Rebin(nrebin)
            var_list.append(h)

        nominal = inputf.Get(inputh)
        nominal.SetDirectory(ROOT.nullptr)
        #nominal.Rebin(nrebin)
        n_bins = nominal.GetNcells()
        up = nominal.Clone()
        up.SetDirectory(ROOT.nullptr)
        up.Reset()
        dn = nominal.Clone()
        dn.SetDirectory(ROOT.nullptr)
        dn.Reset()

        for i in range(0, n_bins+2):
            minimum = float("inf")
            maximum = float("-inf")

            for v in var_list:
                c = v.GetBinContent(i)
                minimum = min(minimum, c)
                maximum = max(maximum, c)

            up.SetBinContent(i, maximum)
            dn.SetBinContent(i, minimum)

        up.Scale(get_bSFratio(bsff, up.GetName()))
        dn.Scale(get_bSFratio(bsff, dn.GetName()))
        up.SetName(inputh + "__" + syst + "up")
        dn.SetName(inputh + "__" + syst + "down")
        #We don't draw pdf in full ana due to computing resources

        up.Write()
        dn.Write()

        if yield_name in inputh:
            up_yield = up.Clone('up_yield')
            dn_yield = dn.Clone('dn_yield')
            up_yield.SetName(inputh.replace(yield_name, yield_name + '_yield') + "__" + syst + "up")
            dn_yield.SetName(inputh.replace(yield_name, yield_name + '_yield') + "__" + syst + "down")
            up_yield.Write()
            dn_yield.Write()


#Check if hadd is already done for MC:
exist_list = {}
for splitname in split_list:
    isExist = os.path.exists(os.path.join(nom_path, splitname + '.root'))
    exist_list[splitname] = isExist

print(exist_list)

for splitname, isExist in exist_list.items():
    if isExist and not forceHadd: continue
    else:
        subprocess.check_call( ["hadd", "-f", os.path.join(nom_path, splitname + '.root')] + glob.glob(os.path.join(nom_path, "split" , splitname) + '*.root') )
    file_list.append(splitname)


# Loop over all files.
for fname in file_list:
    #print(os.path.join(nom_path, fname))
    #if not any(i in fname for i in ['TTTo2L2Nu', 'TTToSemiLeptonic']): continue
    #if not any(i in fname for i in ['hdamp', 'tune']): continue

    #flag for ext. syst with different normalization
    run_on_syst = False
    if any(i in fname for i in ['hdamp', 'tune']):
        run_on_syst = True
        nom_fname = fname.replace('__' + fname.split('__')[1], '')
        nom_file = TFile.Open(os.path.join(nom_path, nom_fname + '.root'), 'READ')
        hcounter_nom = nom_file.Get("hcounter")

    infile = TFile.Open(os.path.join(nom_path, fname + '.root'), 'READ')
    hlists = [ h.GetName() for h in infile.GetListOfKeys() if '_S' in h.GetName() ]
    hlists.append("hcounter")

    # Get ratio for rescaling with b-tagSF.
    if not '__' in fname:
        bSFfile = infile
        if isFFapply:
            bSFfile = TFile.Open(os.path.join(nom_path.replace("_FF",""), fname + '.root'), 'READ')
    elif '__' in fname and any(i in fname for i in ['hdamp', 'tune', 'jes']):#JES uses different bSF per source!
        bSFfile = infile
        if isFFapply:
            bSFfile = TFile.Open(os.path.join(nom_path.replace("_FF",""), fname + '.root'), 'READ')
    else:
        bSFfname = fname.replace('__' + fname.split('__')[1], '')
        bSFfile = TFile.Open(os.path.join(nom_path, bSFfname + '.root'), 'READ')
        if isFFapply:
            bSFfile = TFile.Open(os.path.join(nom_path.replace("_FF",""), bSFfname + '.root'), 'READ')
    #FIXME - ugly...

    # Collecting Histograms in outfile.
    print("Saving histograms at {}/{}.root".format(out_path, fname))
    outfile = TFile.Open(os.path.join(out_path, fname+'.root'), 'RECREATE')

    nominal_list = []

    #Syst flag
    isMEScale = False
    isRenScale = False
    isFacScale = False
    isISR = False
    isFSR = False
    isPDFenv = False
    isPDFas = False

    if any('__mescale' in i for i in hlists): isMEScale = True
    if any('__renscale' in i for i in hlists): isRenScale = True
    if any('__facscale' in i for i in hlists): isFacScale = True
    if any('__isr' in i for i in hlists): isISR = True
    if any('__fsr' in i for i in hlists): isFSR = True
    if any('__pdf' in i.replace("alphas", "") for i in hlists): isPDFenv = True
    if any('__pdfalphas' in i for i in hlists) and 'LFV' not in fname: isPDFas = True

    for hname in hlists:
        if "__" not in hname: nominal_list.append(hname)
        if run_on_syst: continue
        h = infile.Get(hname)
        if yield_name in hname:
            h1 = h.Clone('h1')
            h1.SetName(hname.replace(yield_name, yield_name + '_yield'))
            if "__" not in h1.GetName():
                nominal_list.append(h1.GetName())
            if '201' not in fname or 'jes' in fname: h1.Scale(get_bSFratio(bSFfile, hname))
            h1.Write()
        if any(i in hname for i in ['event', 'counter', '_nobtag', 'LHEPdfWeightSum', 'PSWeightSum', 'ScaleWeightSum']): pass
        elif any(i in hname for i in ['__mescale', '__renscale', '__facscale', '__isr', '__fsr', '__pdf']): continue
        elif '201' in fname and 'jes' not in fname: pass
        else:
            ratio = get_bSFratio(bSFfile, hname)
            h.Scale(ratio)
        h.Write()

    hcounter = infile.Get('hcounter')
    ScaleWeightSum = infile.Get('ScaleWeightSum')
    PSWeightSum = infile.Get('PSWeightSum')
    LHEPdfWeightSum = infile.Get('LHEPdfWeightSum')
    nominal_list = list(set(nominal_list))

    for hname2 in nominal_list:

      if isMEScale: write_envelope(hname2, infile, bSFfile, "mescale", 2, hcounter, ScaleWeightSum)
      if isRenScale: write_envelope(hname2, infile, bSFfile, "renscale", 2, hcounter, ScaleWeightSum)
      if isFacScale: write_envelope(hname2, infile, bSFfile, "facscale", 2, hcounter, ScaleWeightSum)
      if isISR: write_envelope(hname2, infile, bSFfile, "isr", 2, hcounter, PSWeightSum)
      if isFSR: write_envelope(hname2, infile, bSFfile, "fsr", 2, hcounter, PSWeightSum)
      #For PDF: we take 101-102 only for control plots from ttbar
      #if isPDF: write_envelope(hname2, infile, bSFfile, "pdf", 101, hcounter, LHEPdfWeightSum) #sig: 101 / bkg: 101 + 2 (as)
      if isPDFas: write_envelope(hname2, infile, bSFfile, "pdfalphas", 2, hcounter, LHEPdfWeightSum)
      if run_on_syst: rescale(hname2, infile, bSFfile, hcounter, hcounter_nom) #placeholder for hdamp and tune


    infile.Close()
    outfile.Close()


for dataname in data_list:
    try:
        subprocess.call(['rm', os.path.join(out_path, dataname + year + '.root')])
    except: pass
    subprocess.check_call( ["hadd", "-f", os.path.join(out_path, dataname + year + '.root')] + glob.glob(os.path.join(out_path, dataname) + '201*') )
