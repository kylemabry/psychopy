#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""Libraries for wizards, currently firstrun configuration and benchmark.
"""

# Part of the PsychoPy library
# Copyright (C) 2015 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

# Author: Jeremy Gray, Oct 2012; localization 2014

from pyglet.gl import gl_info
import os
import sys
import wx
import numpy as np
import platform
import codecs

if wx.version() < '2.9':
    tmpApp = wx.PySimpleApp()
else:
    tmpApp = wx.App(False)
from psychopy.app import localization  # needed for _translate
from psychopy import (info, data, visual, gui, core, __version__,
                      prefs, event)

_loKeys = {
    'Benchmark', 'benchmark version', 'full-screen', 'dots_circle',
    'dots_square', 'available memory', 'python version', 'locale',
    'Visual', 'openGL version', 'openGL vendor', 'screen size',
    'have shaders', 'refresh stability (SD)', 'no dropped frames',
    'pyglet avbin', 'Audio', 'microphone latency', 'microphone',
    'speakers latency', 'speakers', 'Numeric', 'System', 'platform',
    'internet access', 'auto proxy', 'proxy setting',
    'background processes', 'CPU speed test'}
_localized = {k: _translate(k) for k in _loKeys}


class ConfigWizard(object):
    """Walk through configuration diagnostics & generate report.
    """

    def __init__(self, firstrun=False, interactive=True, log=True):
        """Check drivers, show GUIs, run diagnostics, show report.
        """
        super(ConfigWizard, self).__init__()
        self.firstrun = firstrun
        self.prefs = prefs
        self.appName = 'PsychoPy2'
        self.name = self.appName + _translate(' Configuration Wizard')
        self.reportPath = os.path.join(
            self.prefs.paths['userPrefsDir'], 'firstrunReport.html')
        # self.iconfile = os.path.join(self.prefs.paths['resources'],
        #       'psychopy.png')
        # dlg.SetIcon(wx.Icon(self.iconfile, wx.BITMAP_TYPE_PNG)) # no error
        # but no effect

        dlg = gui.Dlg(title=self.name)
        dlg.addText('')
        if firstrun:
            dlg.addText(_translate("Welcome to PsychoPy2!"), color='blue')
            dlg.addText('')
            msg = "It looks like you are running PsychoPy for the first time."
            dlg.addText(_translate(msg))
            msg = "This wizard will help you get started quickly and smoothly."
            dlg.addText(_translate(msg))
        else:
            dlg.addText(_translate("Welcome to the configuration wizard."))

        # test for fatal configuration errors:
        fatalItemsList = []
        cardInfo = gl_info.get_renderer().replace('OpenGL Engine', '').strip()
        if not driversOkay():
            dlg.addText('')
            dlg.addText(_translate("The first configuration check is your "
                                   "video card's drivers. The current"),
                        color='red')
            dlg.addText(_translate("drivers cannot support PsychoPy, so "
                                   "you'll need to update the drivers."),
                        color='red')
            msg = _translate("""<p>Critical issue:\n</p><p>Your video card (%(card)s) has drivers
                that cannot support the high-performance features that PsychoPy depends on.
                Fortunately, it's typically free and straightforward to get new drivers
                directly from the manufacturer.</p>
                <p><strong>To update the drivers:</strong>
                <li> You'll need administrator privileges.
                <li> On Windows, don't use the windows option to check for updates
                  - it can report that there are no updates available.
                <li> If your card is made by NVIDIA, go to
                  <a href="http://www.nvidia.com/Drivers">the NVIDIA website</a>
                  and use the 'auto detect' option. Try here for
                  <a href="http://support.amd.com/">ATI / Radeon drivers</a>. Or try
                  <a href="http://www.google.com/search?q=download+drivers+%(card2)s">
                  this google search</a> [google.com].
                <li> Download and install the driver.
                <li> Reboot the computer.
                <li> Restart PsychoPy.</p>
                <p>If you updated the drivers and still get this message, you'll
                  need a different video card to use PsychoPy. Click
                <a href="http://www.psychopy.org/installation.html#recommended-hardware">here
                for more information</a> [psychopy.org].</p>
            """)
            fatalItemsList.append(msg % {'card': cardInfo,
                                         'card2': cardInfo.replace(' ', '+')})
        if not cardOkay():
            msg = _translate("""<p>Critical issue:\n</p>""")
            msg += cardInfo
            fatalItemsList.append(msg)
            pass
        # other fatal conditions? append a 'Critical issue' msg to itemsList
        if not fatalItemsList:
            dlg.addText(_translate("We'll go through a series of configura"
                                   "tion checks in about 10 seconds. "))
            dlg.addText('')
            if firstrun:  # explain things more
                dlg.addText(_translate('Note: The display will switch to " '
                                       '"full-screen mode and will '))
                dlg.addText(_translate("then switch back. You don't need "
                                       "to do anything."))
            dlg.addText(_translate('Optional: For best results, please quit'
                                   ' all email programs, web-browsers, '))
            dlg.addText(_translate(
                'Dropbox, backup or sync services, and others.'))
            dlg.addText('')
            dlg.addText(_translate('Click OK to start, or Cancel to skip.'))
            if not self.firstrun:
                dlg.addField(label=_translate('Full details'),
                             initial=self.prefs.app['debugMode'])
        else:
            dlg.addText('')
            dlg.addText(_translate(
                'Click OK for more information, or Cancel to skip.'))

        # show the first dialog:
        dlg.addText('')
        if interactive:
            dlg.show()
        if fatalItemsList:
            self.htmlReport(fatal=fatalItemsList)
            self.save()
            # user ends up in browser:
            url = 'file://' + self.reportPath
            if interactive:
                wx.LaunchDefaultBrowser(url)
            return
        if interactive and not dlg.OK:
            return  # no configuration tests run

        # run the diagnostics:
        verbose = interactive and not self.firstrun and dlg.data[0]
        win = visual.Window(fullscr=interactive, allowGUI=False,
                            monitor='testMonitor', autoLog=log)
        itemsList = self.runDiagnostics(win, verbose)  # sets self.warnings
        win.close()
        self.htmlReport(itemsList)
        self.save()

        # display summary & options:
        dlg = gui.Dlg(title=self.name)
        dlg.addText('')
        dlg.addText(_translate('Configuration testing complete!'))
        summary = self.summary(items=itemsList)
        numWarn = len(self.warnings)
        if numWarn == 0:
            msg = _translate('All values seem reasonable (no warnings).')
        elif numWarn == 1:
            txt = '1 suboptimal value was detected (%s)'
            msg = _translate(txt) % self.warnings[0]
        else:
            txt = '%(num)i suboptimal values were detected (%(warn)s, ...)'
            msg = _translate(txt) % {'num': len(self.warnings),
                                     'warn': self.warnings[0]}
        dlg.addText(msg)
        for item in summary:
            dlg.addText(item[0], item[1])  # (key, color)
        dlg.addText('')
        dlg.addText(_translate(
            'Click OK for full details (will open in a web-browser),'))
        dlg.addText(_translate('or Cancel to stay in PsychoPy.'))
        dlg.addText('')
        if interactive:
            dlg.show()
            if dlg.OK:
                url = 'file://' + self.reportPath
                wx.LaunchDefaultBrowser(url)
        return

    def runDiagnostics(self, win, verbose=False):
        """Return list of (key, val, msg, warn) tuple, set self.warnings

        All tuple elements will be of <type str>.

        msg can depend on val; warn==True indicates a concern.
        Plain text is returned, expected to be used in html <table>.
        Hyperlinks can be embedded as <a href="...">
        """

        report = []  # add item tuples in display order

        # get lots of info and do quick-to-render visual (want 0 frames drop):
        #     for me, grating draw times are: mean 0.53 ms, SD 0.77 ms
        items = info.RunTimeInfo(win=win, refreshTest='grating',
                                 verbose=True, userProcsDetailed=True)

        totalRAM = items['systemMemTotalRAM']
        freeRAM = items['systemMemFreeRAM']
        warn = False
        if freeRAM == 'unknown':
            if totalRAM != 'unknown':
                totalRAM = "%.1fG" % (totalRAM / 1024.)
            txt = 'could not assess available physical RAM; total %s'
            msg = _translate(txt) % totalRAM
            report.append(('available memory', 'unknown', msg, warn))
        else:
            txt = ('physical RAM available for configuration test '
                   '(of %.1fG total)')
            msg = _translate(txt) % (totalRAM / 1024.)
            if freeRAM < 300:  # in M
                txt = ('Warning: low available physical RAM for '
                       'configuration test (of %.1fG total)')
                msg = _translate(txt) % (totalRAM / 1024.)
                warn = True
            report.append(('available memory', unicode(freeRAM) + 'M',
                           msg, warn))

        # ----- PSYCHOPY: -----
        warn = False
        report.append(('PsychoPy', '', '', False))  # not localized
        report.append(('psychopy', __version__,
                       _translate('avoid upgrading during an experiment'),
                       False))
        txt = ('can be set in <a href="http://www.psychopy.org/general/'
               'prefs.html#application-settings-app">Preferences -> App</a>')
        report.append(('locale', items['systemLocale'],
                       _translate(txt), False))
        msg = ''
        if items['pythonVersion'] < '2.5' or items['pythonVersion'] >= '3':
            msg = _translate('Warning: python 2.6 or 2.7 required; '
                             '2.5 is not supported but might work')
            warn = True
        if 'EPD' in items['pythonFullVersion']:
            msg += ' Enthought Python Distribution'
        elif 'PsychoPy2.app' in items['pythonExecutable']:
            msg += ' (PsychoPy StandAlone)'
        bits, linkage = platform.architecture()
        # if not bits.startswith('32'):
        #    msg = 'Warning: 32-bit python required; ' + msg
        report.append(
            ('python version',
             items['pythonVersion'] + ' &nbsp;(%s)' % bits,
             msg, warn))
        warn = False
        if verbose:
            msg = ''
            if items['pythonWxVersion'] < '2.8.10':
                msg = _translate('Warning: wx 2.8.10 or higher required')
                warn = True
            report.append(('wx', items['pythonWxVersion'], '', warn))
            report.append(
                ('pyglet', items['pythonPygletVersion'][:32], '', False))
            report.append(('rush', str(items['psychopyHaveExtRush']),
                           _translate('for high-priority threads'), False))

        # ----- VISUAL: -----
        report.append(('Visual', '', '', False))
        warn = False
        # openGL settings:
        msg = ''
        if items['openGLVersion'] < '2.':
            txt = ('Warning: <a href="http://www.psychopy.org/general/timing'
                   '/reducingFrameDrops.html?highlight=OpenGL+2.0">OpenGL '
                   '2.0 or higher is ideal</a>.')
            msg = _translate(txt)
            warn = True
        report.append(('openGL version', items['openGLVersion'], msg, warn))
        report.append(('openGL vendor', items['openGLVendor'], '', False))
        report.append(('screen size', ' x '.join(
            map(str, items['windowSize_pix'])), '', False))
        # report.append(('wait blanking', str(items['windowWaitBlanking']), '',
        #   False))

        warn = False
        msg = ''
        if not items['windowHaveShaders']:
            txt = ('Warning: <a href="http://www.psychopy.org/general/timing'
                   '/reducingFrameDrops.html?highlight=shader">Rendering of'
                   ' complex stimuli will be slow</a>.')
            msg = _translate(txt)
            warn = True
        report.append(('have shaders', str(
            items['windowHaveShaders']), msg, warn))

        warn = False
        txt = ('during the drifting <a href="http://www.psychopy.org/api/'
               'visual/gratingstim.html">GratingStim</a>')
        msg = _translate(txt)
        if items['windowRefreshTimeMedian_ms'] < 3.3333333:
            txt = ("Warning: too fast? visual sync'ing with the monitor"
                   " seems unlikely at 300+ Hz")
            msg = _translate(txt)
            warn = True
        report.append(('visual sync (refresh)', "%.2f ms/frame" %
                       items['windowRefreshTimeMedian_ms'], msg, warn))
        msg = _translate('SD &lt; 0.5 ms is ideal (want low variability)')
        warn = False
        if items['windowRefreshTimeSD_ms'] > .5:
            txt = ('Warning: the refresh rate has high frame-to-frame '
                   'variability (SD &gt; 0.5 ms)')
            msg = _translate(txt)
            warn = True
        report.append(('refresh stability (SD)', "%.2f ms" %
                       items['windowRefreshTimeSD_ms'], msg, warn))

        # draw 100 dots as a minimally demanding visual test:
        # first get baseline frame-rate (safe as possible, no drawing):
        avg, sd, median = visual.getMsPerFrame(win)
        dots100 = visual.DotStim(
            win, nDots=100, speed=0.005, dotLife=12, dir=90,
            coherence=0.2, dotSize=8, fieldShape='circle', autoLog=False)
        win.recordFrameIntervals = True
        win.frameIntervals = []
        win.flip()
        for i in xrange(180):
            dots100.draw()
            win.flip()
        txt = ('during <a href="http://www.psychopy.org/api/visual/'
               'dotstim.html">DotStim</a> with 100 random dots')
        msg = _translate(txt)
        warn = False
        intervalsMS = np.array(win.frameIntervals) * 1000
        nTotal = len(intervalsMS)
        nDropped = sum(intervalsMS > (1.5 * median))
        if nDropped:
            txt = ('Warning: could not keep up during <a href="http://'
                   'www.psychopy.org/api/visual/dotstim.html">DotStim</a>'
                   ' with 100 random dots.')
            msg = _translate(txt)
            warn = True
        report.append(('no dropped frames', '%i / %i' % (nDropped, nTotal),
                       msg, warn))
        win.recordFrameIntervals = False

        if verbose:
            report.append(('openGL max vertices',
                           str(items['openGLmaxVerticesInVertexArray']),
                           '', False))
            keyList = ('GL_ARB_multitexture', 'GL_EXT_framebuffer_object',
                       'GL_ARB_fragment_program', 'GL_ARB_shader_objects',
                       'GL_ARB_vertex_shader', 'GL_ARB_texture_float',
                       'GL_ARB_texture_non_power_of_two', 'GL_STEREO')
            for key in keyList:
                val = items['openGLext.' + key]  # boolean
                if not val:
                    val = '<strong>' + str(val) + '</strong>'
                report.append((key, str(val), '', False))

        # ----- AUDIO: -----
        report.append(('Audio', '', '', False))
        msg = ''
        warn = False
        if not 'systemPyoVersion' in items:
            msg = _translate(
                'Warning: pyo is needed for sound and microphone.')
            warn = True
            items['systemPyoVersion'] = _translate('(missing)')
        # elif items['systemPyoVersion'] < '0.6.2':
        #    msg = 'pyo 0.6.2 compiled with --no-messages will
        #    suppress start-up messages'
        report.append(('pyo', items['systemPyoVersion'], msg, warn))
        # TO-DO: add microphone + playback as sound test

        # ----- NUMERIC: -----
        report.append(('Numeric', '', '', False))
        report.append(('numpy', items['pythonNumpyVersion'],
                       _translate('vector-based (fast) calculations'), False))
        report.append(('scipy', items['pythonScipyVersion'],
                       _translate('scientific / numerical'), False))
        report.append(('matplotlib', items['pythonMatplotlibVersion'],
                       _translate('plotting; fast contains(), overlaps()'),
                       False))

        # ----- SYSTEM: -----
        report.append(('System', '', '', False))
        report.append(('platform', items['systemPlatform'], '', False))
        msg = _translate('for online help, usage statistics, software '
                         'updates, and google-speech')
        warn = False
        if items['systemHaveInternetAccess'] is not True:
            items['systemHaveInternetAccess'] = 'False'
            msg = _translate('Warning: could not connect (no proxy attempted)')
            warn = True
            # TO-DO: dlg to query whether to try to auto-detect (can take a
            # while), or allow manual entry of proxy str, save into prefs
        val = str(items['systemHaveInternetAccess'])
        report.append(('internet access', val, msg, warn))
        report.append(('auto proxy',
                       str(self.prefs.connections['autoProxy']),
                       _translate('try to auto-detect a proxy if needed; see'
                                  ' <a href="http://www.psychopy.org/general'
                                  '/prefs.html#connection-settings-connection'
                                  's">Preferences -> Connections</a>'),
                       False))
        if not self.prefs.connections['proxy'].strip():
            prx = '&nbsp;&nbsp;--'
        else:
            prx = unicode(self.prefs.connections['proxy'])
        report.append(('proxy setting', prx,
                       _translate('current manual proxy setting from <a '
                                  'href="http://www.psychopy.org/general/'
                                  'prefs.html#connection-settings-connections'
                                  '">Preferences -> Connections</a>'), False))

        txt = 'CPU speed test'
        report.append((txt, "%.3f s" % items['systemTimeNumpySD1000000_sec'],
                       _translate('numpy.std() of 1,000,000 data points'),
                       False))
        # TO-DO: more speed benchmarks
        # - load large image file from disk
        # - transfer image to GPU

        # ----- IMPORTS (relevant for developers & non-StandAlone): -----
        if verbose:  # always False for a real first-run
            report.append((_translate('Python packages'), '', '', False))
            packages = ['PIL', 'openpyxl', 'lxml', 'setuptools', 'pytest',
                        'sphinx', 'psignifit', 'pyserial', 'pp',
                        'pynetstation', 'labjack']
            if sys.platform == 'win32':
                packages.append('pywin32')
                packages.append('winioport')
            for pkg in packages:
                try:
                    if pkg == 'PIL':
                        exec('import PIL.Image')
                        ver = PIL.Image.VERSION
                    # elif pkg == 'lxml':
                    #
                    elif pkg == 'pp':
                        exec('import pp; ver = pp.version')
                    elif pkg == 'pynetstation':
                        exec('from psychopy.hardware import egi')
                        ver = 'import ok'
                    elif pkg == 'pyserial':
                        exec('import serial')
                        ver = serial.VERSION
                    elif pkg == 'pywin32':
                        exec('import win32api')
                        ver = 'import ok'
                    else:
                        exec('import ' + pkg)
                        try:
                            ver = eval(pkg + '.__version__')
                        except Exception:
                            ver = 'import ok'
                    report.append((pkg, ver, '', False))
                except (ImportError, AttributeError):
                    txt = 'could not import package %s'
                    report.append((pkg, '&nbsp;&nbsp;--',
                                   _translate(txt) % pkg, False))

        # rewrite to avoid assumption of locale en_US:
        self.warnings = list(
            set([key for key, val, msg, warn in report if warn]))

        return report

    def summary(self, items=None):
        """Return a list of (item, color) for gui display. For non-fatal items
        """
        config = {}
        for item in items:
            config[item[0]] = [item[1], item[2], item[3]]  # [3] = warn or not
        green = '#009933'
        red = '#CC3300'
        check = u"\u2713   "
        summary = [(check + _translate('video card drivers'), green)]
        ofInterest = ('python version', 'available memory', 'openGL version',
                      'visual sync (refresh)', 'refresh stability (SD)',
                      'no dropped frames', 'internet access')
        #ofInterest.append('background processes')
        for item in ofInterest:
            if not item in config.keys():
                continue  # eg, microphone latency
            if config[item][2]:  # warn True
                summary.append(("X   " + _translate(item), red))
            else:
                summary.append((check + _translate(item), green))
        return summary

    def htmlReport(self, items=None, fatal=False):
        """Return an html report given a list of (key, val, msg, warn) items.

        format triggers: 'Critical issue' in fatal gets highlighted
                         warn==True -> highlight key and val
                         val == msg == '' -> use key as section heading
        """

        imgfile = os.path.join(self.prefs.paths['resources'],
                               'psychopySplash.png')
        _head = (u'<html><head><meta http-equiv="Content-Type" '
                 'content="text/html; charset=utf-8"></head><body>' +
                 '<a href="http://www.psychopy.org"><img src="%s" '
                 'width=396 height=156></a>')
        self.header = _head % imgfile
        # self.iconhtml = '<a href="http://www.psychopy.org"><img src="%s"
        #   width=48 height=48></a>' % self.iconfile
        _foot = _translate('This page was auto-generated by the '
                           'PsychoPy configuration wizard on %s')
        self.footer = ('<center><font size=-1>' +
                      _foot % data.getDateStr(format="%Y-%m-%d, %H:%M") +
                      '</font></center>')

        htmlDoc = self.header
        if fatal:
            # fatal is a list of strings:
            htmlDoc += ('<h2><font color="red">' +
                _translate('Configuration problem') + '</font></h2><hr>')
            for item in fatal:
                item = item.replace('Critical issue', '<p><strong>')
                item += _translate('Critical issue') + '</strong>'
                htmlDoc += item + "<hr>"
        else:
            # items is a list of tuples:
            htmlDoc += ('<h2><font color="green">' +
                _translate('Configuration report') + '</font></h2>\n')
            numWarn = len(self.warnings)
            if numWarn == 0:
                htmlDoc += _translate('<p>All values seem reasonable (no '
                                      'warnings, but there might still be '
                                      'room for improvement).</p>\n')
            elif numWarn == 1:
                _warn = _translate('1 suboptimal value was detected</font>, '
                                   'see details below (%s).</p>\n')
                htmlDoc += ('<p><font color="red">' +
                            _warn % (self.warnings[0]))
            elif numWarn > 1:
                _warn = _translate('%(num)i suboptimal values were detected'
                                   '</font>, see details below (%(warn)s).'
                                   '</p>\n')
                htmlDoc += ('<p><font color="red">' +
                            _warn % {'num': numWarn,
                                     'warn': ', '.join(self.warnings)})
            htmlDoc += '''<script type="text/javascript">
                // Loops through all rows in document and changes display
                // property of rows with a specific ID
                // toggle('ok', '') will display all rows
                // toggle('ok', 'none') hides ok rows, leaving Warning
                // rows shown
                function toggle(ID, display_value) {
                    var tr=document.getElementsByTagName('tr'),
                        i;
                    for (i=0;i<tr.length;i++) {
                        if (tr[i].id == ID) tr[i].style.display = display_value;
                    }
                }
                </script>
                <p>
                <button onClick="toggle('ok', 'none');">'''
            htmlDoc += _translate('Only show suboptimal values') + \
                       '</button>' + \
                        '''<button onClick="toggle('ok', '');">''' + \
                        _translate('Show all information') + '</button></p>'
            htmlDoc += _translate('''<p>Resources:
                  Contributed <a href="http://upload.psychopy.org/benchmark/report.html">benchmarks</a>
                | <a href="http://www.psychopy.org/documentation.html">On-line documentation</a>
                | Download <a href="http://www.psychopy.org/PsychoPyManual.pdf">PDF manual</a>
                | <a href="http://groups.google.com/group/psychopy-users">Search the user-group archives</a>
                </p>''')
            htmlDoc += '<hr><p></p>    <table cellspacing=8 border=0>\n'
            htmlDoc += '    <tr><td><font size=+1><strong>' + \
                       _translate('Configuration test</strong> or setting') +\
                    '</font></td><td><font size=+1><strong>' + _translate('Version or value') +\
                    '</strong></font></td><td><font size=+1><em>' + \
                    _translate('Notes') + '</em></font></td>'
            for (key, val, msg, warn) in items:
                if val == msg == '':
                    key = '<font color="darkblue" size="+1"><strong>' + \
                        _translate(key) + '</strong></font>'
                else:
                    key = '&nbsp;&nbsp;&nbsp;&nbsp;' + _translate(key)
                if warn:
                    key = '<font style=color:red><strong>' + \
                        _translate(key) + '</strong></font>'
                    val = '<font style=color:red><strong>' + val + '</strong></font>'
                    id = 'Warning'
                else:
                    id = 'ok'
                htmlDoc += '        <tr id="%s"><td>' % id
                htmlDoc += key + '</td><td>' + val + '</td><td><em>' + msg + '</em></td></tr>\n'
            htmlDoc += '    </table><hr>'
        htmlDoc += self.footer
        if not fatal and numWarn:
            htmlDoc += """<script type="text/javascript">toggle('ok', 'none'); </script>"""
        htmlDoc += '</body></html>'

        self.reportText = htmlDoc

    def save(self):
        """Save the html text as a file."""
        f = codecs.open(self.reportPath, 'wb', 'UTF8')
        f.write(self.reportText)
        f.close()


class BenchmarkWizard(ConfigWizard):
    """Class to get system info, run benchmarks
    """

    def __init__(self, fullscr=True, interactive=True, log=True):
        super(BenchmarkWizard, self).__init__()
        self.firstrun = False
        self.prefs = prefs
        self.appName = 'PsychoPy2'
        self.name = self.appName + _translate(' Benchmark Wizard')

        dlg = gui.Dlg(title=self.name)
        dlg.addText('')
        dlg.addText(_translate('Benchmarking takes ~20-30 seconds to gather'))
        dlg.addText(_translate('configuration and performance data. Begin?'))
        dlg.addText('')
        if interactive:
            dlg.show()
            if not dlg.OK:
                return

        self._prepare()
        win = visual.Window(fullscr=fullscr, allowGUI=False,
                            monitor='testMonitor', autoLog=False)

        # do system info etc first to get fps, add to list later because
        # it's nicer for benchmark results to appears at top of the report:
        diagnostics = self.runDiagnostics(win, verbose=True)
        info = {}
        for k, v, m, w in diagnostics:
            # list of tuples --> dict, ignore msg m, warning w
            info[k] = v
        fps = 1000. / float(info['visual sync (refresh)'].split()[0])

        itemsList = [('Benchmark', '', '', False)]
        itemsList.append(('benchmark version', '0.1', _translate(
            'dots &amp; configuration'), False))
        itemsList.append(('full-screen', str(fullscr),
                          _translate('visual window for drawing'), False))

        if int(info['no dropped frames'].split('/')[0]) != 0:  # eg, "0 / 180"
            start = 50  # if 100 dots had problems earlier, here start lower
        else:
            start = 200
        for shape in ('circle', 'square'):
            # order matters: circle crashes first
            dotsList = self.runLotsOfDots(win, fieldShape=shape,
                                          starting=start, baseline=fps)
            itemsList.extend(dotsList)
            # start square where circle breaks down
            start = int(dotsList[-1][1])
        itemsList.extend(diagnostics)
        win.close()

        itemsDict = {}
        for itm in itemsList:
            if 'proxy setting' in itm[0] or not itm[1]:
                continue
            itemsDict[itm[0]] = itm[1].replace('<strong>', '').replace(
                '</strong>', '').replace('&nbsp;', '').replace('&nbsp', '')

        # present dialog, upload only if opt-in:
        dlg = gui.Dlg(title=self.name)
        dlg.addText('')
        dlg.addText(_translate(
            'Benchmark complete! (See the Coder output window.)'))

        self.htmlReport(itemsList)
        self.reportPath = os.path.join(self.prefs.paths['userPrefsDir'],
                                       'benchmarkReport.html')
        self.save()
        dlg = gui.Dlg(title=self.name)
        dlg.addText('')
        dlg.addText(_translate(
            'Click OK to view full configuration and benchmark data.'))
        dlg.addText(_translate('Click Cancel to stay in PsychoPy.'))
        dlg.addText('')
        if interactive:
            dlg.show()
            if dlg.OK:
                url = 'file://' + self.reportPath
                wx.LaunchDefaultBrowser(url)

    def _prepare(self):
        """Prep for bench-marking; currently just RAM-related on mac
        """
        if sys.platform == 'darwin':
            try:
                # free up physical memory if possible
                core.shellCall('purge')
            except OSError:
                pass
        elif sys.platform == 'win32':
            # This will run in background, perhaps best to launch it to
            # run overnight the day before benchmarking:
            # %windir%\system32\rundll32.exe advapi32.dll,ProcessIdleTasks
            # rundll32.exe advapi32.dll,ProcessIdleTasks
            pass
        elif sys.platform.startswith('linux'):
            # as root: sync; echo 3 > /proc/sys/vm/drop_caches
            pass
        else:
            pass

    def runLotsOfDots(self, win, fieldShape, starting=100, baseline=None):
        """DotStim stress test: draw many dots until drop lots of frames

        report best dots as the highest dot count at which drop no frames
        fieldShape = circle or square
        starting = initial dot count; increases until failure
        baseline = known frames per second; None means measure it here
        """

        win.recordFrameIntervals = True
        secs = 1  # how long to draw them for, at least 1s

        # baseline frames per second:
        if not baseline:
            for i in xrange(5):
                win.flip()  # wake things up
            win.fps()  # reset
            for i in xrange(60):
                win.flip()
            baseline = round(win.fps())
        maxFrame = round(baseline * secs)

        dotsInfo = []
        win.flip()
        bestDots = starting  # this might over-estimate the actual best
        dotCount = starting
        count = visual.TextStim(win, text=str(dotCount), autoLog=False)
        count.draw()
        win.flip()
        dots = visual.DotStim(win, color=(1.0, 1.0, 1.0), nDots=dotCount,
                              fieldShape=fieldShape, autoLog=False)
        win.fps()  # reset
        frameCount = 0
        while True:
            dots.draw()
            win.flip()
            frameCount += 1
            if frameCount > maxFrame:
                fps = win.fps()  # get frames per sec
                if len(event.getKeys(['escape'])):
                    sys.exit()
                if fps < baseline * 0.6:
                    # only break when start dropping a LOT of frames (80% or
                    # more)
                    dotsInfo.append(
                        ('dots_' + fieldShape, str(bestDots), '', False))
                    break
                frames_dropped = round(baseline - fps)  # can be negative
                if frames_dropped < 1:  # can be negative
                    # only set best if no dropped frames:
                    bestDots = dotCount
                # but do allow to continue in case do better with more dots:
                dotCount += 100
                if dotCount > 1200:
                    dotCount += 100
                if dotCount > 2400:
                    dotCount += 100
                # show the dot count:
                count.setText(str(dotCount), log=False)
                count.draw()
                win.flip()
                dots = visual.DotStim(win, color=(1.0, 1.0, 1.0),
                                      fieldShape=fieldShape, nDots=dotCount,
                                      autoLog=False)
                frameCount = 0
                win.fps()  # reset
        win.recordFrameIntervals = False
        win.flip()
        return tuple(dotsInfo)


def driversOkay():
    """Returns True if drivers should be okay for PsychoPy
    """
    return not 'microsoft' in gl_info.get_vendor().lower()


def cardOkay():
    """Not implemented: Idea = Returns string: okay, maybe, bad
    depending on the graphics card. Currently returns True always
    """

    return True  # until we have a list of known-good cards

    # card = gl_info.get_renderer()
    # knownGoodList = []  # perhaps load from a file
    # if card in knownGoodList:
    #     return True
    # knownBadList = []
    # if card in knownBadList:
    #    return False


if __name__ == '__main__':
    if '--config' in sys.argv:
        ConfigWizard(firstrun=bool('--firstrun' in sys.argv))
    elif '--benchmark' in sys.argv:
        BenchmarkWizard()
    else:
        print("need to specify a wizard in sys.argv, e.g., --benchmark")
