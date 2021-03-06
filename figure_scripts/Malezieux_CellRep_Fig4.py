# -*- coding: utf-8 -*-
"""
Created on Thu Sep  6 10:17:31 2018

@author: Ashley
"""



# Manuscript Malezieux, Kees, Mulle submitted to Cell Reports
# Figure 4
# Description: changes in firing rate with theta



# %% import modules

import os
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib.colors import rgb2hex
from itertools import compress
import matplotlib as mpl


# %% definitions

# eta = event triggered averages.  CHANGE: nans instead of removing events
# VERSION: sample window is more likely to be the same in different recordings
def prepare_eta(signal, ts, event_times, win):
    samp_period = np.round((ts[1] - ts[0]), decimals=3)
    win_npts = [np.round(np.abs(win[0])/samp_period).astype(int),
                np.round(np.abs(win[1])/samp_period).astype(int)]
#    win_npts = [ts[ts < ts[0] + np.abs(win[0])].size,
#                ts[ts < ts[0] + np.abs(win[1])].size]
    et_ts = ts[0:np.sum(win_npts)] - ts[0] + win[0]
    et_signal = np.empty(0)
    if event_times.size > 0:
        if signal.ndim == 1:
            et_signal = np.zeros((et_ts.size, event_times.size))
            for i in np.arange(event_times.size):
                if np.logical_or((event_times[i]+win[0]<ts[0]), (event_times[i]+win[1]>ts[-1])):
                    et_signal[:, i] = np.nan*np.ones(et_ts.size)
                else:
                    # find index of closest timestamp to the event time
                    ind = np.argmin(np.abs(ts-event_times[i]))
                    et_signal[:, i] = signal[(ind - win_npts[0]): (ind + win_npts[1])]
        elif signal.ndim == 2:
            et_signal = np.zeros((signal.shape[0], et_ts.size, event_times.size))
            for i in np.arange(event_times.size):
                if np.logical_or((event_times[i]+win[0]<ts[0]), (event_times[i]+win[1]>ts[-1])):
                    et_signal[:, :, i] = np.nan*np.ones([signal.shape[0], et_ts.size])
                else:
                    # find index of closest timestamp to the event time
                    ind = np.argmin(np.abs(ts-event_times[i]))
                    et_signal[:, :, i] = signal[:, (ind - win_npts[0]):
                                                (ind + win_npts[1])]
    return et_signal, et_ts


# eta = event triggered averages.
# VERSION: sample window is more likely to be the same in different recordings
# VERSION: Keep good part of signal, put nans when recording ends within the window
    # only remove events where there is no recording for the dVm comparison windows
# Note: only for 1d signals
def prepare_eta_keep(signal, ts, event_times, win, dVm_win):
    samp_period = np.round((ts[1] - ts[0]), decimals=3)
    win_npts = [np.round(np.abs(win[0])/samp_period).astype(int),
                np.round(np.abs(win[1])/samp_period).astype(int)]
    #et_ts = ts[0:np.sum(win_npts)] - ts[0] + win[0]
    et_ts = np.arange(win[0], win[1], samp_period)
    et_signal = np.empty(0)
    # pad signal and ts with nans at front and end
    signal = np.concatenate((np.full(win_npts[0], np.nan), signal,
                             np.full(win_npts[1], np.nan)), axis=None)
    ts_pad = np.concatenate((et_ts[:win_npts[0]]+ts[0], ts,
                             et_ts[win_npts[0]:]+ts[-1]), axis=None)
    if event_times.size > 0:
        et_signal = np.zeros((et_ts.size, event_times.size))
        for i in np.arange(event_times.size):
            if np.logical_or((event_times[i]+dVm_win[0]<ts[0]), (event_times[i]+dVm_win[1]>ts[-1])):
                et_signal[:, i] = np.nan*np.ones(et_ts.size)
            else:
                #ind = np.argmin(np.abs(ts-event_times[i])) + win_npts[0]
                ind = np.searchsorted(ts_pad, event_times[i])
                et_signal[:, i] = signal[(ind - win_npts[0]): (ind + win_npts[1])]
    return et_signal, et_ts


# eta = event triggered averages: Version: skip events too close to edge
# VERSION: sample window is more likely to be the same in different recordings
def prepare_eta_skip(signal, ts, event_times, win):
    samp_period = np.round((ts[1] - ts[0]), decimals=3)
    win_npts = [np.round(np.abs(win[0])/samp_period).astype(int),
                np.round(np.abs(win[1])/samp_period).astype(int)]
#    win_npts = [ts[ts < ts[0] + np.abs(win[0])].size,
#                ts[ts < ts[0] + np.abs(win[1])].size]
    et_ts = ts[0:np.sum(win_npts)] - ts[0] + win[0]
    et_signal = np.empty(0)
    if event_times.size > 0:
        # remove any events that are too close to the beginning or end of recording
        if event_times[0]+win[0] < ts[0]:
            event_times = event_times[1:]
        if event_times[-1]+win[1] > ts[-1]:
            event_times = event_times[:-1]
        if signal.ndim == 1:
            et_signal = np.zeros((et_ts.size, event_times.size))
            for i in np.arange(event_times.size):
                # find index of closest timestamp to the event time
                ind = np.argmin(np.abs(ts-event_times[i]))
                et_signal[:, i] = signal[(ind - win_npts[0]): (ind + win_npts[1])]
        elif signal.ndim == 2:
            et_signal = np.zeros((signal.shape[0], et_ts.size, event_times.size))
            for i in np.arange(event_times.size):
                # find index of closest timestamp to the event time
                ind = np.argmin(np.abs(ts-event_times[i]))
                et_signal[:, :, i] = signal[:, (ind - win_npts[0]):
                                            (ind + win_npts[1])]
    return et_signal, et_ts


# eta = event triggered averages
# this code is for point processes, but times instead of inds
def prepare_eta_times(pt_times, event_times, win):
    et_signal = []
    if (pt_times.size > 0) & (event_times.size > 0):
        # find pt_times that occur within window of each event_time
        for i in np.arange(event_times.size):
            ts_section = pt_times[(pt_times > event_times[i] + win[0]) &
                                  (pt_times < event_times[i] + win[1])]
            ts_section = ts_section - event_times[i]
            et_signal.append(ts_section)
    else:
        et_signal = [np.empty(0) for k in np.arange(event_times.size)]
    return et_signal
    
    
# definition for self_calculated variance
def MADAM(data_pts, descriptor):
    v = np.sum(np.abs(data_pts-descriptor))/data_pts.size
    return v



# %% Load data
    
dataset_folder = (r'C:\Users\akees\Documents\Ashley\Papers\MIND 1\Cell Reports\Dryad upload\Dataset')

cell_files = os.listdir(dataset_folder)
data = [{} for k in np.arange(len(cell_files))]
for i in np.arange(len(cell_files)):
    full_file = os.path.join(dataset_folder, cell_files[i])
    data[i] = np.load(full_file, allow_pickle=True).item()


states = [{'id':'theta', 'bef':-2.5, 'aft':0.5, 'samp_time':2, 't_win':[-3, 3]},
          {'id':'LIA', 'bef':-4, 'aft':-1, 'samp_time':2, 't_win':[-4, 2]}]
ntl = ['nost', 'theta', 'LIA']



# %% process data - for dVm vs dFR analysis

# for each cell, find start and stop times for unlabeled times
for i in np.arange(len(data)):
    state_start = np.concatenate([data[i]['theta_start'], data[i]['LIA_start']])
    state_start = np.sort(state_start)
    state_stop = np.concatenate([data[i]['theta_stop'], data[i]['LIA_stop']])
    state_stop = np.sort(state_stop)
    data[i]['nost_start'] = np.append(data[i]['Vm_ds_ts'][0], state_stop)
    data[i]['nost_stop'] = np.append(state_start, data[i]['Vm_ds_ts'][-1])


# for each cell, make a new spike_times for specifically non-spikelets
for i in np.arange(len(data)):
    data[i]['spike_times'] = np.delete(data[i]['sp_times'],
                                       data[i]['spikelets_ind'])


# for each cell, calculate the isi (inter-spike-interval)
# for true spikes only
for i in np.arange(len(data)):
    if data[i]['spike_times'].size > 0:
        isi0 = data[i]['spike_times'][0] - data[i]['Vm_ds_ts'][0]
        data[i]['isi'] = np.ediff1d(data[i]['spike_times'], to_begin=isi0)
    else:
        data[i]['isi'] = np.empty(0)    


# find the (true) spikes that are within bursts
burst_isi = 0.006  # seconds (Mizuseki 2012 0.006)
for i in np.arange(len(data)):
    if data[i]['spike_times'].size > 0:
        burst_bool = 1*(data[i]['isi'] < burst_isi)
        burst_sp = np.where(data[i]['isi'] < burst_isi)[0]
        burst_sp0 = np.where(np.ediff1d(burst_bool) == 1)[0]
        bursts = [None]*len(burst_sp0)
        if burst_sp0.size > 0:
            for j in np.arange(len(burst_sp0)-1):
                inds = np.append(burst_sp0[j], burst_sp[np.logical_and(burst_sp > burst_sp0[j],
                                 burst_sp < burst_sp0[j+1])])
                bursts[j] = data[i]['spike_times'][inds]
            # special case for the last burst:
            j = len(burst_sp0)-1
            inds = np.append(burst_sp0[j], burst_sp[burst_sp > burst_sp0[j]])
            bursts[j] = data[i]['spike_times'][inds]
        data[i]['bursts'] = bursts
    else:
        data[i]['bursts'] = [None]*0

# add windows triggered by start of some brain states
# collect relative times for (true) spikes, singles, doublets, bursts, and CS
for l in np.arange(len(states)):
    for i in np.arange(len(data)):
        t_Vm, t_ts = prepare_eta(data[i]['Vm_s_ds'], data[i]['Vm_ds_ts'],
                                 data[i][states[l]['id']+'_start'],
                                 states[l]['t_win'])
        t_sp = prepare_eta_times(data[i]['sp_times'],
                                    data[i][states[l]['id']+'_start'],
                                    states[l]['t_win'])
        t_spike = prepare_eta_times(data[i]['spike_times'],
                                    data[i][states[l]['id']+'_start'],
                                    states[l]['t_win'])
        spikelet_times = data[i]['sp_times'][data[i]['spikelets_ind'].astype(int)]
        t_spikelet = prepare_eta_times(spikelet_times,
                                    data[i][states[l]['id']+'_start'],
                                    states[l]['t_win'])
        single_times = data[i]['sp_times'][data[i]['singles_ind'].astype(int)]
        t_single = prepare_eta_times(single_times,
                                     data[i][states[l]['id']+'_start'],
                                     states[l]['t_win'])
        if data[i]['doublets_ind'].size > 0:
            doublet_times = data[i]['sp_times'][data[i]['doublets_ind'][0]]
        else:
            doublet_times = np.empty(0)
        t_doublet = prepare_eta_times(doublet_times,
                                     data[i][states[l]['id']+'_start'],
                                     states[l]['t_win'])
        burst_times = np.array([d[0] for d in data[i]['bursts']])
        t_burst = prepare_eta_times(burst_times,
                                     data[i][states[l]['id']+'_start'],
                                     states[l]['t_win'])
        t_CS = prepare_eta_times(data[i]['CS_start'],
                                     data[i][states[l]['id']+'_start'],
                                     states[l]['t_win'])
        data[i][states[l]['id']+'_Vm'] = t_Vm
        data[i][states[l]['id']+'_sp'] = t_sp  # all spikes and spikelets
        data[i][states[l]['id']+'_spike'] = t_spike  # all spikes (no spikelets)
        data[i][states[l]['id']+'_spikelet'] = t_spikelet
        data[i][states[l]['id']+'_single'] = t_single
        data[i][states[l]['id']+'_doublet'] = t_doublet
        data[i][states[l]['id']+'_burst'] = t_burst
        data[i][states[l]['id']+'_CS'] = t_CS
    states[l]['t_ts'] = t_ts


# add windows triggered by start of some brain states
# collect relative times for (true) spikes, singles, doublets, bursts, and CS
for l in np.arange(len(states)):
    for i in np.arange(len(data)):
        single_times = data[i]['sp_times'][data[i]['singles_ind'].astype(int)]
        if data[i]['doublets_ind'].size > 0:
            doublet_times = np.concatenate(data[i]['sp_times'][data[i]['doublets_ind']])
        else:
            doublet_times = np.empty(0)
        nonCS_times = np.sort(np.concatenate((single_times, doublet_times)))
        t_nonCS = prepare_eta_times(nonCS_times,
                                     data[i][states[l]['id']+'_start'],
                                     states[l]['t_win'])
        if len(data[i]['CS_ind']) > 0:
            CS_times = data[i]['sp_times'][np.concatenate(data[i]['CS_ind'])]
        else:
            CS_times = np.empty(0)
        t_CS = prepare_eta_times(CS_times,
                                     data[i][states[l]['id']+'_start'],
                                     states[l]['t_win'])
        data[i][states[l]['id']+'_CS_spikes'] = t_CS
        data[i][states[l]['id']+'_nonCS_spikes'] = t_nonCS





# %% event-based organization for dVm vs dFR
        

# make a dictionary to hold values collapsed over all cells
events = [{}  for k in np.arange(len(states))]
# find Vm0, dVm and significance for each run, excluding when Ih is changed
for l in np.arange(len(states)):
    all_c_p = np.empty(0)
    all_Ih = np.empty(0)
    all_Vm0 = np.empty(0)
    all_dVm = np.empty(0)
    all_dVm_p = np.empty(0)
    for i in np.arange(len(data)):
        samp_freq = 1/(data[i]['Vm_ds_ts'][1] - data[i]['Vm_ds_ts'][0])
        num_ind = int(states[l]['samp_time']*samp_freq)
        # find index of dIh_times
        dIh_ind = data[i]['dIh_times']*samp_freq
        dIh_ind = dIh_ind.astype(int)
        c_p = np.zeros(data[i][states[l]['id']+'_start'].size)
        Ih = np.zeros(data[i][states[l]['id']+'_start'].size)
        Vm0 = np.zeros(data[i][states[l]['id']+'_start'].size)
        dVm = np.zeros(data[i][states[l]['id']+'_start'].size)
        dVm_p = np.zeros(data[i][states[l]['id']+'_start'].size)
        for j in np.arange(data[i][states[l]['id']+'_start'].size):
            # find indices
            bef_ind = int(np.sum(data[i]['Vm_ds_ts'] <
                          (data[i][states[l]['id']+'_start'][j] + states[l]['bef'])))
            aft_ind = int(np.sum(data[i]['Vm_ds_ts'] <
                          (data[i][states[l]['id']+'_start'][j] + states[l]['aft'])))
            # put nan if times are straddling a time when dIh is changed
            dIh_true = np.where((dIh_ind > bef_ind) & (dIh_ind < aft_ind + num_ind))[0]
            if dIh_true.size > 0:
                Ih[j] = np.nan
                Vm0[j] = np.nan
                dVm[j] = np.nan
                dVm_p[j] = np.nan
            else:
                if np.logical_or(l==0, l==1):
                    c_p[j] = data[i][states[l]['id']+'_cell_p']
                else:
                    c_p[j] = data[i]['theta_cell_p']
                Ih_ind = np.searchsorted(data[i]['Vm_Ih_ts'],
                                         data[i][states[l]['id']+'_start'][j])
                Ih[j] = data[i]['Vm_Ih'][Ih_ind]
                # test whether Vm values are significantly different
                # Welch's t-test: normal, unequal variances, independent samp
                t, p = stats.ttest_ind(data[i]['Vm_ds'][bef_ind:bef_ind+num_ind],
                                       data[i]['Vm_ds'][aft_ind:aft_ind+num_ind],
                                       equal_var=False, nan_policy='omit')
                dVm_p[j] = p
                if (np.nanmean(data[i]['Vm_ds'][aft_ind:aft_ind+num_ind]) - 
                    np.nanmean(data[i]['Vm_ds'][bef_ind:bef_ind+num_ind])) > 0:
                    Vm0[j] = np.nanmin(data[i]['Vm_s_ds'][bef_ind:bef_ind+num_ind])
                    dVm[j] = (np.nanmax(data[i]['Vm_s_ds'][aft_ind:aft_ind+num_ind]) - 
                              np.nanmin(data[i]['Vm_s_ds'][bef_ind:bef_ind+num_ind]))
                else:
                    Vm0[j] = np.nanmax(data[i]['Vm_s_ds'][bef_ind:bef_ind+num_ind])
                    dVm[j] = (np.nanmin(data[i]['Vm_s_ds'][aft_ind:aft_ind+num_ind]) - 
                              np.nanmax(data[i]['Vm_s_ds'][bef_ind:bef_ind+num_ind]))
        data[i][states[l]['id']+'_c_p'] = c_p
        data[i][states[l]['id']+'_Ih'] = Ih
        data[i][states[l]['id']+'_Vm0'] = Vm0
        data[i][states[l]['id']+'_dVm'] = dVm
        data[i][states[l]['id']+'_dVm_p'] = dVm_p
        all_c_p = np.append(all_c_p, c_p)
        all_Ih = np.append(all_Ih, Ih)
        all_Vm0 = np.append(all_Vm0, Vm0)
        all_dVm = np.append(all_dVm, dVm)
        all_dVm_p = np.append(all_dVm_p, dVm_p)
    events[l]['c_p'] = all_c_p
    events[l]['Ih'] = all_Ih
    events[l]['Vm0'] = all_Vm0
    events[l]['dVm'] = all_dVm
    events[l]['dVm_p'] = all_dVm_p


## add windows triggered by start of some brain states
#for l in np.arange(len(states)):
#    for i in np.arange(len(data)):
#        t_Vm, t_ts = prepare_eta(data[i]['Vm_s_ds'], data[i]['Vm_ds_ts'],
#                                 data[i][states[l]['id']+'_start'],
#                                 states[l]['t_win'])
#        t_sp = prepare_eta_times(data[i]['sp_times'],
#                                 data[i][states[l]['id']+'_start'],
#                                 states[l]['t_win'])
#        data[i][states[l]['id']+'_Vm'] = t_Vm
#        data[i][states[l]['id']+'_sp'] = t_sp
#    states[l]['t_ts'] = t_ts 


# add windows triggered by start of some brain states
for l in np.arange(len(states)):
    for i in np.arange(len(data)):
        dVm_win = [states[l]['bef'], states[l]['aft']+states[l]['samp_time']]
        t_Vm, t_ts = prepare_eta_keep(data[i]['Vm_s_ds'], data[i]['Vm_ds_ts'],
                                 data[i][states[l]['id']+'_start'],
                                 states[l]['t_win'], dVm_win)
        t_sp = prepare_eta_times(data[i]['sp_times'],
                                 data[i][states[l]['id']+'_start'],
                                 states[l]['t_win'])
        data[i][states[l]['id']+'_Vm'] = t_Vm
        data[i][states[l]['id']+'_sp'] = t_sp
    states[l]['t_ts'] = t_ts 


# add triggered windows to event dictionary
# VERSION: only removes events with all nans (not any nans)
for l in np.arange(len(events)):
    raster_sp = []
    psth_sp = np.empty(0)
    Vm = np.empty((states[l]['t_ts'].shape[0], 0))
    duration = np.empty(0)
    cell_id = np.empty(0)
    for i in np.arange(len(data)):
        cell_psth_sp = np.empty(0)
        if data[i][states[l]['id']+'_start'].size > 0:
            Vm = np.append(Vm, data[i][states[l]['id']+'_Vm'], axis=1)
            duration = np.append(duration, (data[i][states[l]['id']+'_stop'] -
                                     data[i][states[l]['id']+'_start']))
            if isinstance(data[i]['cell_id'], str):
                ind = data[i]['cell_id'].find('_')
                cell_int = int(data[i]['cell_id'][:ind])*np.ones(data[i][states[l]['id']+'_start'].size)
                cell_id = np.append(cell_id, cell_int)
            else:
                cell_int = data[i]['cell_id']*np.ones(data[i][states[l]['id']+'_start'].size)
                cell_id = np.append(cell_id, cell_int)
            for j in np.arange(data[i][states[l]['id']+'_start'].size):
                psth_sp = np.append(psth_sp, data[i][states[l]['id']+'_sp'][j])
                cell_psth_sp = np.append(cell_psth_sp, data[i][states[l]['id']+'_sp'][j])
                raster_sp.append(data[i][states[l]['id']+'_sp'][j])
            data[i][states[l]['id']+'_psth_sp'] = cell_psth_sp
    # remove nans
    no_nan = np.logical_and([~np.isnan(Vm).all(axis=0)],
                            [~np.isnan(events[l]['Vm0'])]).flatten()
#    no_nan = np.logical_and([~np.isnan(Vm).any(axis=0)],
#                            [~np.isnan(events[l]['Vm0'])]).flatten()
    events[l]['Vm'] = Vm[:, no_nan]
    events[l]['cell_id'] = cell_id[no_nan]
    events[l]['duration'] = duration[no_nan]
    events[l]['raster_sp'] = list(compress(raster_sp, no_nan))
    events[l]['c_p'] = events[l]['c_p'][no_nan]
    events[l]['Ih'] = events[l]['Ih'][no_nan]
    events[l]['Vm0'] = events[l]['Vm0'][no_nan]
    events[l]['dVm'] = events[l]['dVm'][no_nan]
    events[l]['dVm_p'] = events[l]['dVm_p'][no_nan]


    


# %% set figure parameters


# set colors
# states
c_run_theta = [0.398, 0.668, 0.547]
c_nonrun_theta = [0.777, 0.844, 0.773]
c_LIA = [0.863, 0.734, 0.582]
# response type
c_hyp = [0.184, 0.285, 0.430]
c_dep = [0.629, 0.121, 0.047]
c_no = [1, 1, 1]
c_lhyp = [0.62, 0.71, 0.84]
c_ldep = [0.97, 0.71, 0.67]
# dependent variables
c_sp = [0.398, 0.461, 0.703]
c_Vm = [0.398, 0.461, 0.703]
# other
c_lgry = [0.75, 0.75, 0.75]
c_mgry = [0.5, 0.5, 0.5]
c_dgry = [0.25, 0.25, 0.25]
c_wht = [1, 1, 1]
c_blk = [0, 0, 0]
c_bwn = [0.340, 0.242, 0.125]
c_lbwn = [0.645, 0.484, 0.394]
c_grn = [0.148, 0.360, 0.000]

c_dVm = [c_hyp, c_mgry, c_dep]
c_state = [c_run_theta, c_LIA, c_mgry]

# set style defaults
mpl.rcParams['font.size'] = 8
mpl.rcParams['savefig.dpi'] = 1200
mpl.rcParams['lines.linewidth'] = 1.5
mpl.rcParams['font.sans-serif'] = "Arial"
mpl.rcParams['font.family'] = "sans-serif"
mpl.rcParams['axes.spines.right'] = False
mpl.rcParams['axes.spines.top'] = False
mpl.rcParams['axes.linewidth'] = 1
mpl.rcParams['xtick.major.size'] = 4
mpl.rcParams['xtick.major.width'] = 1
mpl.rcParams['ytick.major.size'] = 4
mpl.rcParams['ytick.major.width'] = 1
mpl.rcParams['boxplot.whiskerprops.linestyle'] = '-'
mpl.rcParams['patch.force_edgecolor'] = True
mpl.rcParams['patch.facecolor'] = 'b'


# set figure output folder
fig_folder = r'C:\Users\akees\Documents\Ashley\Figures\2020-05_Paper_MIND1\Fig4'



# %% make figures - scatters for dFR vs dVm

l = 0       
state='theta'

# event-based dVm vs dFR
# prep numbers for dVm
all_dVm = np.array([d[state+'_mean_dVm'] for d in data])[[isinstance(d['cell_id'], int) for d in data]]
all_cell_p = np.array([d[state+'_cell_p'] for d in data])[[isinstance(d['cell_id'], int) for d in data]]
cell_hyp_sig = all_dVm[all_cell_p < 0.05]
cell_hyp_no = all_dVm[(all_dVm < 0) & (all_cell_p >= 0.05)]
cell_dep_sig = all_dVm[all_cell_p > 0.95]
cell_dep_no = all_dVm[(all_dVm > 0) & (all_cell_p <= 0.95)]
# prep number for firing rate
bin_width = 0.25  # seconds
bins = np.arange(states[l]['t_win'][0], states[l]['t_win'][1], bin_width)
unique_cells = [isinstance(d['cell_id'], int) for d in data]
fr_bef = np.zeros(len(data))
fr_aft = np.zeros(len(data))
for i in np.arange(len(data)):
    H_c, bins = np.histogram(np.concatenate(data[i][state+'_spike']), bins)
    H_c = H_c/(len(data[i][state+'_spike'])*bin_width)
    x = H_c[2:10]
    y = H_c[14:22]
    fr_bef[i] = np.mean(x)
    fr_aft[i] = np.mean(y)
fr_bef = fr_bef[unique_cells]
fr_aft = fr_aft[unique_cells]
fr_diff = fr_aft-fr_bef
all_cell_p = np.array([d[state+'_cell_p'] for d in data])[unique_cells]
cell_hyp_sig_fr = fr_diff[all_cell_p < 0.05]
cell_hyp_no_fr = fr_diff[(all_dVm < 0) & (all_cell_p >= 0.05)]
cell_dep_sig_fr = fr_diff[all_cell_p > 0.95]
cell_dep_no_fr = fr_diff[(all_dVm > 0) & (all_cell_p <= 0.95)]
# Event-based correlation between dVm and dFR - all true spikes
fig, ax = plt.subplots(1, figsize=[2.3, 2.3])
n = 0
for i in np.arange(len(data)):
    for j in np.arange(data[i][state+'_start'].size):
        x = data[i][state+'_dVm'][j]
        fr_bef = np.logical_and(data[i][state+'_spike'][j] > states[l]['bef'],
                                data[i][state+'_spike'][j] < states[l]['bef'] + states[l]['samp_time'])
        fr_bef = np.sum(fr_bef)/states[l]['samp_time']
        fr_aft = np.logical_and(data[i][state+'_spike'][j] > states[l]['aft'],
                                data[i][state+'_spike'][j] < states[l]['aft'] + states[l]['samp_time'])
        fr_aft = np.sum(fr_aft)/states[l]['samp_time']
        if np.logical_and(fr_aft == 0, fr_bef == 0):
            y = np.nan
        else:
            y = fr_aft-fr_bef
            n = n+1
        z = data[i][state+'_dVm_p'][j]
        if z > 0.05:
            ax.scatter(x, y, s=5, facecolors='none', edgecolors=c_mgry, alpha=1, zorder=1)
        elif x < 0:
            ax.scatter(x, y, s=5, facecolors=c_lhyp, edgecolors=c_lhyp, alpha=1, zorder=2)
        elif x > 0:
            ax.scatter(x, y, s=5, facecolors=c_ldep, edgecolors=c_ldep, alpha=1, zorder=2)
ax.axhline(0, linestyle='--', color=c_blk, zorder=1)
ax.axvline(0, linestyle='--', color=c_blk, zorder=1)
ax.set_ylim([-18, 18])
ax.set_xlim([-18, 18])
ax.set_xticks([-15, -10, -5, 0, 5, 10, 15])
ax.set_yticks([-15, -10, -5, 0, 5, 10, 15])
ax.set_xticklabels(['', -10, '', 0, '', 10, ''])
ax.set_yticklabels(['', -10, '', 0, '', 10, ''])
ax.set_xlabel(r'$\Delta$ Vm (mV)')
ax.set_ylabel(r'$\Delta$ firing rate (Hz)')          
fig.tight_layout()
plt.savefig(os.path.join(fig_folder, 'dFR_vs_dVm_event_'+state+'.png'), transparent=True)

# cell-based dFR vs dVm
all_dVm = np.array([d[state+'_mean_dVm'] for d in data])[[isinstance(d['cell_id'], int) for d in data]]
all_cell_p = np.array([d[state+'_cell_p'] for d in data])[[isinstance(d['cell_id'], int) for d in data]]
cell_hyp_sig = all_dVm[all_cell_p < 0.05]
cell_hyp_no = all_dVm[(all_dVm < 0) & (all_cell_p >= 0.05)]
cell_dep_sig = all_dVm[all_cell_p > 0.95]
cell_dep_no = all_dVm[(all_dVm > 0) & (all_cell_p <= 0.95)]
# prep number for firing rate
bin_width = 0.25  # seconds
bins = np.arange(states[l]['t_win'][0], states[l]['t_win'][1], bin_width)
unique_cells = [isinstance(d['cell_id'], int) for d in data]
fr_bef = np.zeros(len(data))
fr_aft = np.zeros(len(data))
for i in np.arange(len(data)):
    H_c, bins = np.histogram(np.concatenate(data[i][state+'_spike']), bins)
    H_c = H_c/(len(data[i][state+'_spike'])*bin_width)
    x = H_c[2:10]
    y = H_c[14:22]
    fr_bef[i] = np.mean(x)
    fr_aft[i] = np.mean(y)
fr_bef = fr_bef[unique_cells]
fr_aft = fr_aft[unique_cells]
fr_diff = fr_aft-fr_bef
all_cell_p = np.array([d[state+'_cell_p'] for d in data])[unique_cells]
cell_hyp_sig_fr = fr_diff[all_cell_p < 0.05]
cell_hyp_no_fr = fr_diff[(all_dVm < 0) & (all_cell_p >= 0.05)]
cell_dep_sig_fr = fr_diff[all_cell_p > 0.95]
cell_dep_no_fr = fr_diff[(all_dVm > 0) & (all_cell_p <= 0.95)]
# plot the scatter for cells
fig, ax = plt.subplots(1, figsize=[2.3, 2.3])
ax.axhline(0, linestyle='--', color=c_blk, zorder=1)
ax.axvline(0, linestyle='--', color=c_blk, zorder=1)
ax.set_ylim([-8, 3])
ax.set_xlim([-8, 3])
ax.set_xticks([-6, -4, -2, 0, 2])
ax.set_yticks([-6, -4, -2, 0, 2])
ax.set_xlabel(r'mean $\Delta$ Vm (mV)')
ax.set_ylabel(r'mean $\Delta$ firing rate (Hz)')          
s_cell = 20
ax.scatter(cell_hyp_sig, cell_hyp_sig_fr, s=s_cell, facecolors=c_hyp,
           edgecolors=c_blk, zorder=4, alpha=1)
ax.scatter(cell_hyp_no, cell_hyp_no_fr, s=s_cell, facecolors='none',
           edgecolors=c_blk, zorder=3, alpha=1)
ax.scatter(cell_dep_sig, cell_dep_sig_fr, s=s_cell, facecolors=rgb2hex(c_dep),
           edgecolors=c_blk, zorder=4, alpha=1)
ax.scatter(cell_dep_no, cell_dep_no_fr, s=s_cell, facecolors='none',
           edgecolors=c_blk, zorder=3, alpha=1)
fig.tight_layout()
plt.savefig(os.path.join(fig_folder, 'dFR_vs_dVm_cell_'+state+'.png'), transparent=True)




#%% firing raster and psth for all hyp/dep events
# VERSION: hyp and dep in same figure for alignment and relative sizing

l = 0       
state='theta'


# raster and psth for all hyp events
cond = np.logical_and((events[l]['dVm_p'] < 0.05), (events[l]['dVm'] < 0))
raster = list(compress(events[l]['raster_sp'], cond))
raster_cells = events[l]['cell_id'][cond]
# remove the events when the cell is not spiking
cond = np.array([d.size for d in raster]) > 0
raster = list(compress(raster, cond))
raster_cells = raster_cells[cond]
# find the number of events per cell, resort according to the raster
unique_cells, ind, counts = np.unique(raster_cells, return_index=True, return_counts=True)
order = np.argsort(ind)
unique_cells = unique_cells[order]
ind = ind[order]
counts = np.cumsum(counts[order])
# plot the raster
fig, axs = plt.subplots(4, 1, sharex=True, figsize=(2.2, 4),
                        gridspec_kw = {'height_ratios':[3, 1, 1, 1]})
for j in np.arange(len(raster)):
    r = axs[0].eventplot(raster[j], orientation='horizontal',
                         lineoffsets=(j+0.5), linelengths=0.75,
                         color=[[c_hyp]])
axs[0].axis('tight')
axs[0].set_ylim([0, len(raster)])
axs[0].set_yticks(counts)
axs[0].set_yticklabels([])
axs[0].set_ylabel('events')
axs[0].tick_params(bottom=False)
axs[0].spines['bottom'].set_visible(False)
# plot the psth
bin_width = 0.25  # seconds
bins = np.arange(states[l]['t_win'][0], states[l]['t_win'][1]+bin_width, bin_width)
H, bins = np.histogram(np.concatenate(raster), bins)
H = H/(len(raster)*bin_width)
axs[1].bar(bins[:-1], H, width=bin_width, color=c_hyp, align='edge')
axs[1].axis('tight')
axs[1].set_yticks([5, 10])
axs[1].set_xticks([-2, 0, 2])
axs[1].set_ylabel('firing rate (Hz)')
# raster and psth for all dep events
cond = np.logical_and((events[l]['dVm_p'] < 0.05), (events[l]['dVm'] > 0))
raster = list(compress(events[l]['raster_sp'], cond))
raster_cells = events[l]['cell_id'][cond]
# remove the events when the cell is not spiking
cond = np.array([d.size for d in raster]) > 0
raster = list(compress(raster, cond))
raster_cells = raster_cells[cond]
# find the number of events per cell, resort according to the raster
unique_cells, ind, counts = np.unique(raster_cells, return_index=True, return_counts=True)
order = np.argsort(ind)
unique_cells = unique_cells[order]
ind = ind[order]
counts = np.cumsum(counts[order])
# plot the raster
for j in np.arange(len(raster)):
    r = axs[2].eventplot(raster[j], orientation='horizontal',
                         lineoffsets=(j+0.5), linelengths=0.75,
                         color=[[c_dep]])
axs[2].axis('tight')
axs[2].set_ylim([0, len(raster)])
axs[2].set_yticks(counts)
axs[2].set_yticklabels([])
axs[2].set_ylabel('events')
axs[2].tick_params(bottom=False)
axs[2].spines['bottom'].set_visible(False)
# plot the psth
bin_width = 0.25  # seconds
bins = np.arange(states[l]['t_win'][0], states[l]['t_win'][1]+bin_width, bin_width)
H, bins = np.histogram(np.concatenate(raster), bins)
H = H/(len(raster)*bin_width)
axs[3].bar(bins[:-1], H, width=bin_width, color=c_dep, align='edge')
axs[3].axis('tight')
axs[3].set_yticks([5, 10])
axs[3].set_xticks([-2, 0, 2])
axs[3].set_ylabel('firing rate (Hz)')
axs[3].set_xlabel('time relative to theta onset (s)')
plt.tight_layout()
plt.savefig(os.path.join(fig_folder, 'raster_hypdep_'+state+'_.png'), transparent=True)


