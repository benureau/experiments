import os

from environments import tools
from clusterjobs import context

from ..tools import chrono
from .. import jobs
from ..execute import populate_grp

_already_loaded = {}



class Data(object):

    def load_history(self, name='datafile'):
        path = self.job.context.fullpath(self.job.jobcfg.hardware[name])
        #os.path.join(self.expcfg.meta.rootpath, self.expcfg.exp.path, self.job.jobcfg.hardware.datafile)
        return chrono.ChronoHistory(path, extralog=False, verbose=self.verbose)

    def __getitem__(self, key):
        return self.data[key]

    def load(self):
        if self.key in _already_loaded:
            self.data = _already_loaded[self.key]
        else:
            self._load()
            _already_loaded[self.key] = self.data
        return self.data

class DataResults(Data):

    def __init__(self, expcfg, testname='', verbose=True, load=True):
        self.expcfg   = expcfg
        self.testname = testname
        self.verbose  = verbose

        ctx = context.Context(expcfg.meta.rootpath, expcfg.exp.path)
        job_dict = populate_grp(expcfg)
        self.job = job_dict['results'][testname][0]

        self.rep = self.job.jobcfg.rep
        self.key = self.job.jobcfg.key
        if load:
            self.load()

    def _load(self):
        history = self.load_history()

        self.data = {'job': self.job,
                     'ticks': [], 'avg': [], 'std': [],
                     'tick_avgs': [], 'tick_stds': [],
                     'rep_avgs':[[] for _ in range(self.rep)],
                     'rep_stds':[[] for _ in range(self.rep)]}

        for t, entry in enumerate(history.core.entries):
            if entry is not None:
                self.data['ticks'].append(entry['t'])
                for key in ['avg', 'std']:
                    self.data[key].append(entry['data'][key])
                self.data['tick_avgs'].append(entry['data']['error_avgs'])
                self.data['tick_stds'].append(entry['data']['error_stds'])
                for r in range(self.rep):
                    self.data['rep_avgs'][r].append(entry['data']['error_avgs'][r])
                    self.data['rep_stds'][r].append(entry['data']['error_stds'][r])


class DataExploration(Data):

    def __init__(self, expcfg, rep, verbose=True, load=True):
        self.expcfg  = expcfg
        self.verbose = verbose
        self.rep     = rep

        ctx = context.Context(expcfg.meta.rootpath, expcfg.exp.path)
        job_dict = populate_grp(expcfg)
        self.job = job_dict['explorations'][rep]

        self.key = self.job.jobcfg.key
        if load:
            self.load()

    def _load(self):
        history = self.load_history()

        self.m_channels = history.core.meta['m_channels']
        self.s_channels = history.core.meta['s_channels']

        self.data = {'ticks': [], 'explorations': [], 'observations': [],
                     's_signals': [], 's_vectors': [], 's_goals': [],
                     'm_signals': [], 'm_vectors': [],
                     's_channels': self.s_channels, 'm_channels': self.m_channels}

        for t, entry in enumerate(history.core.entries):
            if entry is not None:
                exploration = entry['data']['exploration']
                feedback    = entry['data']['feedback']
                m_signal = exploration['m_signal']
                s_signal = feedback['s_signal']
                self.data['ticks'].append(t)
                self.data['explorations'].append((exploration, feedback))
                self.data['observations'].append((m_signal, s_signal))
                self.data['m_signals'].append(m_signal)
                self.data['s_signals'].append(s_signal)
                self.data['m_vectors'].append(tools.to_vector(m_signal, self.m_channels))
                self.data['s_vectors'].append(tools.to_vector(s_signal, self.s_channels))


class DataSensoryExploration(DataExploration):

    def _load(self):
        history = self.load_history(name='sensoryfile')

        self.m_channels = history.core.meta['m_channels']
        self.s_channels = history.core.meta['s_channels']

        self.data = {'ticks': [], 's_signals': [],
                     's_channels': self.s_channels, 'm_channels': self.m_channels}

        for t, entry in enumerate(history.core.entries):
            if entry is not None:
                feedback = entry['data']['feedback']
                s_signal = feedback['s_signal']
                self.data['ticks'].append(t)
                self.data['s_signals'].append(s_signal)
                self.data['s_vectors'].append(tools.to_vector(s_signal, self.s_channels))


def load_exploration(expcfg, rep=0, sensory=False, verbose=True):
    if sensory:
        return DataSensoryExploration(expcfg, rep, verbose=verbose)
    else:
        return DataExploration(expcfg, rep, verbose=verbose)

def load_result(expcfg, testname, verbose=True):
    return DataResults(expcfg, testname, verbose=verbose)

def load_results(expcfgs_grid, testname, mask=None, verbose=True):
    g = []
    for expcfgs_row in expcfgs_grid:
        g.append([])
        if mask is None:
            mask = [True for _ in expcfgs_row]
        for flag, expcfg in zip(mask, expcfgs_row):
            if not flag or expcfg is None:
                g[-1].append(None)
            else:
                g[-1].append(load_result(expcfg, testname, verbose=verbose))

    return g

def load_explorations(expcfgs_grid, rep=0, sensory=False, verbose=True):
    g = []
    for expcfgs_row in expcfgs_grid:
        g.append([])
        for expcfg in expcfgs_row:
            g[-1].append(load_exploration(expcfg, rep=rep, sensory=sensory, verbose=verbose))
    return g