/**
 * Buzzer alarm via Web Audio API — tanpa file audio eksternal.
 * Sirine dua nada (880/620 Hz square wave) yang bergantian cepat.
 *
 * Kebijakan autoplay browser: AudioContext hanya boleh bunyi setelah
 * gesture user. primeAudio() dipanggil dari handler klik (saat memicu
 * simulasi) supaya context sudah aktif ketika alarm menyala dari timer.
 */

let ctx = null
let nodes = null

export function primeAudio() {
  const AC = window.AudioContext || window.webkitAudioContext
  if (!AC) return
  if (!ctx) ctx = new AC()
  if (ctx.state === 'suspended') ctx.resume()
}

export function startBuzzer() {
  if (!ctx || nodes) return
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = 'square'
  osc.frequency.value = 880
  gain.gain.value = 0.06
  osc.connect(gain)
  gain.connect(ctx.destination)
  osc.start()
  let hi = true
  const iv = setInterval(() => {
    hi = !hi
    osc.frequency.setValueAtTime(hi ? 880 : 620, ctx.currentTime)
  }, 220)
  nodes = { osc, gain, iv }
}

export function stopBuzzer() {
  if (!nodes) return
  clearInterval(nodes.iv)
  nodes.osc.stop()
  nodes.osc.disconnect()
  nodes.gain.disconnect()
  nodes = null
}
