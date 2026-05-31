/**
 * Copyright (c) 2026 Enzien Audio, Ltd.
 * 
 * Redistribution and use in source and binary forms, with or without modification,
 * are permitted provided that the following conditions are met:
 * 
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions, and the following disclaimer.
 * 
 * 2. Redistributions in binary form must reproduce the phrase "powered by heavy",
 *    the heavy logo, and a hyperlink to https://enzienaudio.com, all in a visible
 *    form.
 * 
 *   2.1 If the Application is distributed in a store system (for example,
 *       the Apple "App Store" or "Google Play"), the phrase "powered by heavy"
 *       shall be included in the app description or the copyright text as well as
 *       the in the app itself. The heavy logo will shall be visible in the app
 *       itself as well.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 * 
 */

#ifndef _HEAVY_CONTEXT_PROJECTNAME_HPP_
#define _HEAVY_CONTEXT_PROJECTNAME_HPP_

// object includes
#include "HeavyContext.hpp"
#include "HvSignalRPole.h"
#include "HvMath.h"
#include "HvSignalVar.h"
#include "HvControlVar.h"
#include "HvSignalPhasor.h"
#include "HvControlSystem.h"
#include "HvControlBinop.h"
#include "HvSignalDel1.h"

class Heavy_ProjectName : public HeavyContext {

 public:
  Heavy_ProjectName(double sampleRate, int poolKb=10, int inQueueKb=2, int outQueueKb=0);
  ~Heavy_ProjectName();

  const char *getName() override { return "ProjectName"; }
  int getNumInputChannels() override { return 2; }
  int getNumOutputChannels() override { return 1; }

  int process(float **inputBuffers, float **outputBuffer, int n) override;
  int processInline(float *inputBuffers, float *outputBuffer, int n) override;
  int processInlineInterleaved(float *inputBuffers, float *outputBuffer, int n) override;

  int getParameterInfo(int index, HvParameterInfo *info) override;
  struct Parameter {
    struct In {
      enum ParameterIn : hv_uint32_t {
        ATTENV_FM_ADC2 = 0x7D61C9AD, // attenv_fm_adc2
        BASE_PITCH_ADC1 = 0x249B65CC, // base_pitch_adc1
      };
    };
  };

 private:
  HvTable *getTableForHash(hv_uint32_t tableHash) override;
  void scheduleMessageForReceiver(hv_uint32_t receiverHash, HvMessage *m) override;


  /*
  * Code for expr~ implementation
  * Write out the generic header code
  */

  // per class code

  // per object code


  // static sendMessage functions
  static void cVar_QHsKYuUG_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cMsg_HGDKF9vW_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cSystem_9YIrlu4j_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_ajYrhvDH_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_T075qREA_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cMsg_P98tyiaY_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_yb0ZhyYy_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_SqBlwgo7_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_4ZMAWAf3_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cVar_dVzuS280_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cMsg_8meCoVYk_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cSystem_QLlVppGx_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_VKUwU6bb_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_VKtLj6G1_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cMsg_rP1S369z_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_QUa3G0yJ_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_U8JwHRhC_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_FxgbL9bZ_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cReceive_eCKUiDfu_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cReceive_ypUlWAEp_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cReceive_xDzO6VUw_sendMessage(HeavyContextInterface *, int, const HvMessage *);

  // objects
  SignalRPole sRPole_CF6edapS;
  SignalRPole sRPole_pfHU8K4u;
  SignalPhasor sPhasor_vFifgqb5;
  SignalVarf sVarf_mgofxbUJ;
  ControlVar cVar_QHsKYuUG;
  ControlBinop cBinop_ajYrhvDH;
  ControlBinop cBinop_T075qREA;
  SignalVarf sVarf_7klUey4b;
  ControlBinop cBinop_yb0ZhyYy;
  ControlBinop cBinop_SqBlwgo7;
  ControlBinop cBinop_4ZMAWAf3;
  SignalVarf sVarf_hE81qZtw;
  SignalVarf sVarf_sWiUl8qn;
  ControlVar cVar_dVzuS280;
  ControlBinop cBinop_VKUwU6bb;
  ControlBinop cBinop_VKtLj6G1;
  SignalVarf sVarf_crFINwfC;
  ControlBinop cBinop_QUa3G0yJ;
  ControlBinop cBinop_U8JwHRhC;
  ControlBinop cBinop_FxgbL9bZ;
  SignalVarf sVarf_jV5lUmnI;
};

#endif // _HEAVY_CONTEXT_PROJECTNAME_HPP_
