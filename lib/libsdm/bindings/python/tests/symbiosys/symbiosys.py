#!/usr/bin/python
import os
import sys
import time
import sdm
import time

sdm.var.log_level  = sdm.FATAL_LOG | sdm.ERR_LOG | sdm.WARN_LOG
sdm.var.log_level |= sdm.NOTE_LOG

sdm.var.log_level |= sdm.INFO_LOG | sdm.DEBUG_LOG | sdm.ASYNC_LOG

signal_file = "../../../../../../examples/0717-up.dat"
log_dir_base = "signals/" + time.strftime("%Y%m%d-%H%M/")
interval    = 5

config = {'samples': 25600,
          'threshold': 350,
          'gain': 0,
          'src_lvl': 3,
          'pream_gain': 0,
          'usbl_pream_gain': 13}

#########################################################################
def session_config(session):
    sdm.send_config(session, config['threshold'], \
                             config['gain'],      \
                             config['src_lvl'],   \
                             config['pream_gain'])
    sdm.expect(session, sdm.REPLY_REPORT, sdm.REPLY_REPORT_CONFIG)

    sdm.send_usbl_config(session, 0, config['samples'],\
                                     config['usbl_pream_gain'], 4)
    sdm.expect(session, sdm.REPLY_REPORT, sdm.REPLY_REPORT_USBL_CONFIG)

def waitsync_setup(session):
    sdm.send_config(session, 0, \
                             config['gain'],      \
                             config['src_lvl'],   \
                             config['pream_gain'])
    sdm.expect(session, sdm.REPLY_REPORT, sdm.REPLY_REPORT_CONFIG)

    sdm.send_usbl_config(session, 0, config['samples'],\
                                     config['usbl_pream_gain'], 4)

    sdm.expect(session, sdm.REPLY_REPORT, sdm.REPLY_REPORT_USBL_CONFIG);


#########################################################################
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("%s: IP-active IP-passive" % sys.argv[0])
        exit(1)

    active_hosts  = [sys.argv[1]]
    passive_hosts = sys.argv[2:]

    hosts = active_hosts + passive_hosts

    if not os.path.exists(log_dir_base):
        os.makedirs(log_dir_base)

    sessions    = []
    for host in hosts:
        ss = sdm.create_session(host, host)
        session_config(ss)
        sessions.append(ss)
    active   = sessions[0]
    passives = sessions[1:]

    for ss in sessions:
        sdm.add_sink_membuf(ss);
        sdm.send_rx(ss, 0)

    sdm.logger(sdm.NOTE_LOG, "====== workaround: reading 2 sec ======\n")
    # handle incoming data for a microsecond time
    sdm.receive_data_time_limit(sessions, 2000)
    #sdm.logger(sdm.NOTE_LOG, "========\n")

    for ss in sessions:
        sdm.expect(ss, sdm.REPLY_STOP);

    for ss in sessions:
        waitsync_setup(ss)

    sdm.logger(sdm.NOTE_LOG, "====== waiting waitsynin ======\n")
    sdm.waitsyncin(active)
    sdm.logger(sdm.NOTE_LOG, "!!!!!! event   waitsynin !!!!!!!!!\n")

    sdm.logger(sdm.NOTE_LOG, "====== setup rx for passive ======\n")
    for ss in passives:
        sdm.add_sink(ss, log_dir_base + "rcv-" + ss.name + ".raw");
        sdm.send_rx(ss, config['samples'])

    sdm.logger(sdm.NOTE_LOG, "====== send signal from active ======\n")
    sdm.send_signal_file(active, signal_file, signal_file)

    sdm.logger(sdm.NOTE_LOG, "====== setup rx for active ======\n")
    sdm.add_sink(active, log_dir_base + "rcv-" + active.name + ".raw");
    sdm.send_rx(active, config['samples'])

    sdm.logger(sdm.NOTE_LOG, "====== receive on passive ======\n")
    for ss in passives:
        sdm.expect(ss, sdm.REPLY_STOP);

    sdm.logger(sdm.NOTE_LOG, "====== receive on active ======\n")
    sdm.expect(active, sdm.REPLY_STOP);
    #sdm.receive_data_time_limit(sessions, 2000)

    sdm.logger(sdm.NOTE_LOG, "====== get USBL data ==========\n")
    for ss in sessions:
        sdm.receive_usbl_data(ss, config['samples'], log_dir_base + "u%d-" + ss.name + ".raw");

        ss.time = sdm.receive_systime(ss)

    i = 0
    for ss in sessions:
        diration = 0

        # is active side
        if i == 0:
            diration = (float(ss.time.rx) - float(ss.time.tx)) / 1000.

        out = "%s;%d;%d;%d;%d;%d\n" % (ss.name,
                                       ss.time.current,
                                       ss.time.tx,
                                       ss.time.rx,
                                       ss.time.syncin,
                                       diration)

        sdm.logger(sdm.NOTE_LOG, out)
        f = open(log_dir_base + "systime-" + ss.name + ".txt", "w")
        f.write(out)
        f.close()
        i += 1


