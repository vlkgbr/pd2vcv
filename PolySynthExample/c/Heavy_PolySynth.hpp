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

#ifndef _HEAVY_CONTEXT_POLYSYNTH_HPP_
#define _HEAVY_CONTEXT_POLYSYNTH_HPP_

// object includes
#include "HeavyContext.hpp"
#include "HvControlBinop.h"
#include "HvSignalPhasor.h"
#include "HvMath.h"
#include "HvControlVar.h"
#include "HvControlSystem.h"
#include "HvSignalRPole.h"
#include "HvSignalDel1.h"
#include "HvSignalVar.h"

class Heavy_PolySynth : public HeavyContext {

 public:
  Heavy_PolySynth(double sampleRate, int poolKb=10, int inQueueKb=2, int outQueueKb=0);
  ~Heavy_PolySynth();

  const char *getName() override { return "PolySynth"; }
  int getNumInputChannels() override { return 2; }
  int getNumOutputChannels() override { return 1; }

  int process(float **inputBuffers, float **outputBuffer, int n) override;
  int processInline(float *inputBuffers, float *outputBuffer, int n) override;
  int processInlineInterleaved(float *inputBuffers, float *outputBuffer, int n) override;

  int getParameterInfo(int index, HvParameterInfo *info) override;
  struct Parameter {
    struct In {
      enum ParameterIn : hv_uint32_t {
        ATTENV_DRIVE = 0x9EDB4CD, // attenv_drive
        BASE_DRIVE_ADC2 = 0xDB3A8A65, // base_drive_adc2
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
  static void cVar_b2JZ97Rp_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cMsg_v4hKq1dI_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cSystem_8lyAa5u6_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_zpNzeIZ1_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_NPLhuXbP_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cMsg_fQyUQPWC_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_KSZX8mSr_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_CRTaNx9z_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_HblJFp5C_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cVar_bG6wT9mD_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cMsg_lppHJUBp_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cSystem_npossoch_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_QZyrDo4f_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_MkRXsCj8_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cMsg_2HsTxoXU_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_vkrV0ZAS_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_8P0ql5kG_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cBinop_kiedzOjZ_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cReceive_mBGnOeSy_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cReceive_Rr93Xtgk_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cReceive_xkfmaUhT_sendMessage(HeavyContextInterface *, int, const HvMessage *);
  static void cReceive_xOgQWYqq_sendMessage(HeavyContextInterface *, int, const HvMessage *);

  // objects
  SignalRPole sRPole_ZyuGBcva;
  SignalPhasor sPhasor_aljpczW1;
  SignalRPole sRPole_TWjA9bfs;
  SignalVarf sVarf_2hiQxDCH;
  ControlVar cVar_b2JZ97Rp;
  ControlBinop cBinop_zpNzeIZ1;
  ControlBinop cBinop_NPLhuXbP;
  SignalVarf sVarf_b80iZ7AG;
  ControlBinop cBinop_KSZX8mSr;
  ControlBinop cBinop_CRTaNx9z;
  ControlBinop cBinop_HblJFp5C;
  SignalVarf sVarf_e85nOe0j;
  SignalVarf sVarf_7wzvnLEg;
  ControlVar cVar_bG6wT9mD;
  ControlBinop cBinop_QZyrDo4f;
  ControlBinop cBinop_MkRXsCj8;
  SignalVarf sVarf_hic1dfhp;
  ControlBinop cBinop_vkrV0ZAS;
  ControlBinop cBinop_8P0ql5kG;
  ControlBinop cBinop_kiedzOjZ;
  SignalVarf sVarf_hRiIZjTG;
  SignalVarf sVarf_C6fJkiWd;
};

#endif // _HEAVY_CONTEXT_POLYSYNTH_HPP_
