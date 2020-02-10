%module sdm

%typemap(in,numinputs=0,noblock=1) size_t *len {
//int16_t* stream_load_samples(char *filename, size_t *len);
%typemap(in, numinputs=0, noblock=1) size_t *len {
  size_t templen;
  $1 = &templen;
}

%typemap(out) uint16_t *stream_load_samples {
    int i;
    $result = PyList_New(templen);
    for (i = 0; i < templen; i++)
        PyList_SetItem($result, i, PyInt_FromLong((double)$1[i]));
}

%typemap(freearg) uint16_t *stream_load_samples {
  if ($1)
      free($1);
}

%{
#include <sdm.h>
#include <stream.h>
#include <stdio.h> /* fopen() */
#include <utils.h> /* logger() */
%}

%include <sdm.h>
%include <stream.h>


%typemap(in) (size_t nsamples, uint16_t *data) {
    int i;

    if (!PyList_Check($input)) {
        PyErr_SetString(PyExc_ValueError, "Expecting a list");
        return NULL;
    }
    $1 = PyList_Size($input);
    $2 = (uint16_t *) malloc(($1)*sizeof(uint16_t));
    for (i = 0; i < $1; i++) {
        PyObject *s = PyList_GetItem($input,i);
        if (!PyInt_Check(s)) {
            free($2);
            PyErr_SetString(PyExc_ValueError, "List items must be integers");
            return NULL;
        }
        $2[i] = PyInt_AsLong(s);
    }
}

%typemap(freearg) (size_t nsamples, uint16_t *data) {
    if ($2)
        free($2);
}

%inline %{

int sdm_cmd_ref(sdm_session_t *ss, size_t nsamples, uint16_t *data) {
    if (nsamples != 1024) {
        logger (WARN_LOG, "Error reference signal must be 1024 samples\n");
        return -1;
    }
    return sdm_cmd(ss, SDM_CMD_REF, data, nsamples);
}

int sdm_cmd_tx(sdm_session_t *ss, size_t nsamples, uint16_t *data) {
    int rc;
    uint16_t cmd;
    size_t cnt, passed = 0, len = 1024;

    cmd = SDM_CMD_TX;
    do {
        len = len < nsamples - passed ? len : nsamples - passed;

        cnt = len;
        data += cnt;
        if (cnt == 0) {
            cmd = SDM_CMD_STOP;
            break;
        }

        if (cnt == len && nsamples >= 1024) {
            rc = sdm_cmd(ss, cmd, nsamples, data, len);
            passed += len;
        } else if (cnt > 0) {
            uint16_t buf[1024] = {0};
            memcpy(buf, data, cnt);
            rc = sdm_cmd(ss, cmd, nsamples, buf, 1024 * ((cnt + 1023) / 1024));
            passed += 1024 * ((cnt + 1023) / 1024);
        } else {
            rc = -1;
        }
        cmd = SDM_CMD_TX_CONTINUE;
    } while (rc == 0 && passed < nsamples);
}

int sdm_cmd_rx_to_file(sdm_session_t *ss, char *filename, size_t len) {
    FILE *fp;

    /* 16776192 == 0xfffffc maximum 24 bit digit rounded to 1024 */
    if (len < 0 && len > 16776192) {
        logger (ERR_LOG, "%s(): must be in range from 0 to 16776192\n", __func__);
        return -1;
    }

    /* truncate file if exist */
    if ((fp = fopen(filename, "w")) == NULL) {
        logger(ERR_LOG, "Error cannot open %s file: %s\n", filename, strerror(errno));
        return -1;
    }
    fclose(fp);

    if (len % 1024) {
        long old = len;
        len += 1024 - len % 1024;
        logger(WARN_LOG, "Warning: signal samples number %ld do not divisible by 1024 samples."
                " Expand to %ld\n" , old, len);
    }

    if (ss->filename) {
        free(ss->filename);
    }
    ss->filename = strdup(filename);

    sdm_cmd(ss, SDM_CMD_RX, len);
}

%}

