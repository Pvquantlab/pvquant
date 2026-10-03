/** Dört adım kartlarının levha illüstrasyonları — V1 "Mürekkep & Güneş"
 *  (kaynak: vitrin-gorsel-kesif/varyant-1.html; veri-türevi çizgi dili, süs olduğu için aria-hidden).
 *  Renk sınıfları vitrin.css'te .vt-dg-* altında token'lara bağlı; mavi=tahmin, amber=gerçekleşen
 *  sözleşmesi illüstrasyonda da korunur. */
const CIZIMLER = {
  1: (
      <svg className="vt-dg" viewBox="0 0 420 130" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false"><path className="vt-dg-i" d="M16 114H404"/>
      <circle className="vt-dg-s vt-dg-sd" cx="52" cy="34" r="13"/>
      <path className="vt-dg-s" d="M71.0,34.0L79.0,34.0"/>
      <path className="vt-dg-s" d="M65.4,47.4L71.1,53.1"/>
      <path className="vt-dg-s" d="M52.0,53.0L52.0,61.0"/>
      <path className="vt-dg-s" d="M38.6,47.4L32.9,53.1"/>
      <path className="vt-dg-s" d="M33.0,34.0L25.0,34.0"/>
      <path className="vt-dg-s" d="M38.6,20.6L32.9,14.9"/>
      <path className="vt-dg-s" d="M52.0,15.0L52.0,7.0"/>
      <path className="vt-dg-s" d="M65.4,20.6L71.1,14.9"/>
      <path className="vt-dg-i vt-dg-kes" d="M66 42L174 95.8M68 34L204 82.4M70 28L234 69"/>
      <path className="vt-dg-c" d="M178 102V114M270 61V114"/>
      <rect className="vt-dg-c vt-dg-d" x="-70" y="-5" width="140" height="10" rx="2.5" transform="translate(224 78) rotate(-24)"/>
      <path className="vt-dg-i" d="M300 114V30"/>
      <path className="vt-dg-i vt-dg-kes" d="M316.0,111.6 L319.0,110.3 L322.0,108.3 L325.0,105.6 L328.0,101.9 L331.0,97.2 L334.0,91.4 L337.0,84.6 L340.0,76.8 L343.0,68.4 L346.0,59.9 L349.0,51.7 L352.0,44.5 L355.0,38.8 L358.0,35.2 L361.0,34.0 L364.0,35.2 L367.0,38.8 L370.0,44.5 L373.0,51.7 L376.0,59.9 L379.0,68.4 L382.0,76.8 L385.0,84.6 L388.0,91.4 L391.0,97.2 L394.0,101.9 L397.0,105.6 L400.0,108.3 L403.0,110.3 L406.0,111.6 L409.0,112.5"/>
      <path className="vt-dg-i vt-dg-kes" d="M312 52H410"/>
      <path className="vt-dg-c" d="M316.0,111.9 L319.0,110.6 L322.0,108.9 L325.0,106.4 L328.0,103.1 L331.0,98.9 L334.0,93.7 L337.0,87.5 L340.0,80.5 L343.0,73.0 L346.0,65.3 L349.0,57.9 L352.0,52.0 L355.0,52.0 L358.0,52.0 L361.0,52.0 L364.0,52.0 L367.0,52.0 L370.0,52.0 L373.0,57.9 L376.0,65.3 L379.0,73.0 L382.0,80.5 L385.0,87.5 L388.0,93.7 L391.0,98.9 L394.0,103.1 L397.0,106.4 L400.0,108.9 L403.0,110.6 L406.0,111.9 L409.0,112.7"/></svg>
  ),
  2: (
      <svg className="vt-dg" viewBox="0 0 420 130" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false"><path className="vt-dg-i" d="M16 114H404M24 114V14"/>
      <path className="vt-dg-i vt-dg-kes" d="M24.0,113.5 L28.0,113.4 L32.0,113.2 L36.0,113.0 L40.0,112.8 L44.0,112.5 L48.0,112.1 L52.0,111.7 L56.0,111.2 L60.0,110.6 L64.0,109.9 L68.0,109.1 L72.0,108.1 L76.0,107.1 L80.0,105.8 L84.0,104.4 L88.0,102.9 L92.0,101.1 L96.0,99.1 L100.0,97.0 L104.0,94.6 L108.0,92.0 L112.0,89.2 L116.0,86.3 L120.0,83.1 L124.0,79.8 L128.0,76.3 L132.0,72.7 L136.0,69.0 L140.0,65.2 L144.0,61.4 L148.0,57.6 L152.0,53.9 L156.0,50.3 L160.0,46.9 L164.0,43.6 L168.0,40.7 L172.0,38.0 L176.0,35.6 L180.0,33.6 L184.0,32.1 L188.0,30.9 L192.0,30.2 L196.0,30.0 L200.0,30.2 L204.0,30.9 L208.0,32.1 L212.0,33.6 L216.0,35.6 L220.0,38.0 L224.0,40.7 L228.0,43.6 L232.0,46.9 L236.0,50.3 L240.0,53.9 L244.0,57.6 L248.0,61.4 L252.0,65.2 L256.0,69.0 L260.0,72.7 L264.0,76.3 L268.0,79.8 L272.0,83.1 L276.0,86.3 L280.0,89.2 L284.0,92.0 L288.0,94.6 L292.0,97.0 L296.0,99.1 L300.0,101.1 L304.0,102.9 L308.0,104.4 L312.0,105.8 L316.0,107.1 L320.0,108.1 L324.0,109.1 L328.0,109.9 L332.0,110.6 L336.0,111.2 L340.0,111.7 L344.0,112.1 L348.0,112.5 L352.0,112.8 L356.0,113.0 L360.0,113.2 L364.0,113.4 L368.0,113.5 L372.0,113.6 L376.0,113.7 L380.0,113.8 L384.0,113.8 L388.0,113.9 L392.0,113.9 L396.0,113.9 L400.0,113.9 L404.0,114.0"/>
      <path className="vt-dg-i" d="M60,110.0V110.6"/>
      <path className="vt-dg-i" d="M88,110.4V102.9"/>
      <path className="vt-dg-i" d="M116,99.1V86.3"/>
      <path className="vt-dg-i" d="M144,87.2V61.4"/>
      <path className="vt-dg-i" d="M172,51.1V38.0"/>
      <path className="vt-dg-i" d="M200,39.2V30.2"/>
      <path className="vt-dg-i" d="M228,34.5V43.6"/>
      <path className="vt-dg-i" d="M256,65.4V69.0"/>
      <path className="vt-dg-i" d="M284,82.2V92.0"/>
      <path className="vt-dg-i" d="M312,105.8V105.8"/>
      <path className="vt-dg-i" d="M340,107.4V111.7"/>
      <path className="vt-dg-i" d="M368,110.4V113.5"/>
      <path className="vt-dg-t" d="M24.0,113.0 L28.0,113.0 L32.0,113.0 L36.0,113.0 L40.0,113.0 L44.0,113.0 L48.0,113.0 L52.0,113.0 L56.0,113.0 L60.0,113.0 L64.0,113.0 L68.0,113.0 L72.0,112.9 L76.0,112.7 L80.0,112.5 L84.0,112.2 L88.0,111.7 L92.0,111.2 L96.0,110.5 L100.0,109.6 L104.0,108.6 L108.0,107.3 L112.0,105.8 L116.0,104.1 L120.0,102.1 L124.0,99.8 L128.0,97.2 L132.0,94.4 L136.0,91.2 L140.0,87.8 L144.0,84.2 L148.0,80.3 L152.0,76.3 L156.0,72.1 L160.0,67.9 L164.0,63.6 L168.0,59.3 L172.0,55.1 L176.0,51.2 L180.0,47.4 L184.0,43.9 L188.0,40.8 L192.0,38.1 L196.0,35.9 L200.0,34.2 L204.0,33.0 L208.0,32.3 L212.0,32.3 L216.0,32.8 L220.0,33.9 L224.0,35.4 L228.0,37.5 L232.0,40.0 L236.0,43.0 L240.0,46.2 L244.0,49.8 L248.0,53.5 L252.0,57.4 L256.0,61.4 L260.0,65.4 L264.0,69.4 L268.0,73.3 L272.0,77.0 L276.0,80.6 L280.0,84.0 L284.0,87.2 L288.0,90.2 L292.0,92.9 L296.0,95.3 L300.0,97.5 L304.0,99.5 L308.0,101.3 L312.0,102.8 L316.0,104.2 L320.0,105.4 L324.0,106.4 L328.0,107.3 L332.0,108.1 L336.0,108.8 L340.0,109.4 L344.0,110.0 L348.0,110.5 L352.0,110.9 L356.0,111.3 L360.0,111.6 L364.0,111.9 L368.0,112.2 L372.0,112.5 L376.0,112.7 L380.0,112.9 L384.0,113.0 L388.0,113.0 L392.0,113.0 L396.0,113.0 L400.0,113.0 L404.0,113.0"/>
      <circle className="vt-dg-gn" cx="60" cy="110.0" r="3.6"/>
      <circle className="vt-dg-gn" cx="88" cy="110.4" r="3.6"/>
      <circle className="vt-dg-gn" cx="116" cy="99.1" r="3.6"/>
      <circle className="vt-dg-gn" cx="144" cy="87.2" r="3.6"/>
      <circle className="vt-dg-gn" cx="172" cy="51.1" r="3.6"/>
      <circle className="vt-dg-gn" cx="200" cy="39.2" r="3.6"/>
      <circle className="vt-dg-gn" cx="228" cy="34.5" r="3.6"/>
      <circle className="vt-dg-gn" cx="256" cy="65.4" r="3.6"/>
      <circle className="vt-dg-gn" cx="284" cy="82.2" r="3.6"/>
      <circle className="vt-dg-gn" cx="312" cy="105.8" r="3.6"/>
      <circle className="vt-dg-gn" cx="340" cy="107.4" r="3.6"/>
      <circle className="vt-dg-gn" cx="368" cy="110.4" r="3.6"/></svg>
  ),
  3: (
      <svg className="vt-dg" viewBox="0 0 420 130" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false"><path className="vt-dg-i" d="M16 118H404"/>
      <path className="vt-dg-tb" d="M28.0,65.0 L34.0,65.0 L40.0,65.1 L46.0,65.1 L52.0,65.0 L58.0,64.9 L64.0,64.8 L70.0,64.6 L76.0,64.3 L82.0,63.9 L88.0,63.4 L94.0,62.9 L100.0,62.2 L106.0,61.5 L112.0,60.7 L118.0,59.8 L124.0,58.8 L130.0,57.7 L136.0,56.6 L142.0,55.4 L148.0,54.1 L154.0,52.8 L160.0,51.5 L166.0,50.2 L172.0,48.9 L178.0,47.5 L184.0,46.3 L190.0,45.0 L196.0,43.8 L202.0,42.7 L208.0,41.6 L214.0,40.6 L220.0,39.7 L226.0,38.8 L232.0,38.1 L238.0,37.4 L244.0,36.9 L250.0,36.4 L256.0,36.0 L262.0,35.7 L268.0,35.5 L274.0,35.4 L280.0,35.3 L286.0,35.2 L292.0,35.2 L298.0,35.2 L304.0,35.3 L310.0,35.3 L316.0,35.3 L322.0,35.3 L328.0,35.3 L334.0,35.2 L340.0,35.1 L346.0,34.9 L352.0,34.6 L358.0,34.2 L364.0,33.8 L370.0,33.2 L376.0,32.6 L382.0,31.8 L388.0,31.0 L394.0,30.1 L400.0,29.1 L400.0,119.1 L394.0,118.8 L388.0,118.4 L382.0,118.0 L376.0,117.4 L370.0,116.8 L364.0,116.0 L358.0,115.2 L352.0,114.2 L346.0,113.2 L340.0,112.2 L334.0,111.0 L328.0,109.8 L322.0,108.6 L316.0,107.3 L310.0,106.0 L304.0,104.6 L298.0,103.3 L292.0,102.0 L286.0,100.7 L280.0,99.5 L274.0,98.3 L268.0,97.1 L262.0,96.1 L256.0,95.1 L250.0,94.1 L244.0,93.3 L238.0,92.6 L232.0,91.9 L226.0,91.4 L220.0,90.9 L214.0,90.6 L208.0,90.3 L202.0,90.1 L196.0,89.9 L190.0,89.8 L184.0,89.8 L178.0,89.8 L172.0,89.8 L166.0,89.9 L160.0,89.9 L154.0,89.9 L148.0,89.9 L142.0,89.9 L136.0,89.8 L130.0,89.6 L124.0,89.4 L118.0,89.1 L112.0,88.7 L106.0,88.3 L100.0,87.7 L94.0,87.1 L88.0,86.3 L82.0,85.5 L76.0,84.6 L70.0,83.6 L64.0,82.5 L58.0,81.4 L52.0,80.2 L46.0,78.9 L40.0,77.6 L34.0,76.3 L28.0,75.0 Z"/>
      <path className="vt-dg-i" d="M407,29.1h5V119.1h-5"/>
      <path className="vt-dg-t" d="M28.0,70.0 L34.0,70.7 L40.0,71.3 L46.0,72.0 L52.0,72.6 L58.0,73.2 L64.0,73.6 L70.0,74.1 L76.0,74.4 L82.0,74.7 L88.0,74.9 L94.0,75.0 L100.0,75.0 L106.0,74.9 L112.0,74.7 L118.0,74.4 L124.0,74.1 L130.0,73.7 L136.0,73.2 L142.0,72.6 L148.0,72.0 L154.0,71.4 L160.0,70.7 L166.0,70.0 L172.0,69.3 L178.0,68.7 L184.0,68.0 L190.0,67.4 L196.0,66.9 L202.0,66.4 L208.0,65.9 L214.0,65.6 L220.0,65.3 L226.0,65.1 L232.0,65.0 L238.0,65.0 L244.0,65.1 L250.0,65.3 L256.0,65.5 L262.0,65.9 L268.0,66.3 L274.0,66.8 L280.0,67.4 L286.0,68.0 L292.0,68.6 L298.0,69.3 L304.0,69.9 L310.0,70.6 L316.0,71.3 L322.0,71.9 L328.0,72.5 L334.0,73.1 L340.0,73.6 L346.0,74.0 L352.0,74.4 L358.0,74.7 L364.0,74.9 L370.0,75.0 L376.0,75.0 L382.0,74.9 L388.0,74.7 L394.0,74.5 L400.0,74.1"/>
      <circle className="vt-dg-gn" cx="52" cy="74.5" r="3.8"/>
      <circle className="vt-dg-gn" cx="96" cy="70.2" r="3.8"/>
      <circle className="vt-dg-gn" cx="146" cy="80.6" r="3.8"/>
      <circle className="vt-dg-gn" cx="198" cy="60.7" r="3.8"/>
      <circle className="vt-dg-gn" cx="250" cy="80.7" r="3.8"/>
      <circle className="vt-dg-gn" cx="300" cy="53.3" r="3.8"/>
      <circle className="vt-dg-gn" cx="348" cy="86.0" r="3.8"/>
      <circle className="vt-dg-gn" cx="392" cy="51.0" r="3.8"/></svg>
  ),
  4: (
      <svg className="vt-dg" viewBox="0 0 420 130" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false"><path className="vt-dg-i" d="M16 118H404"/>
      <rect className="vt-dg-b" x="32" y="106" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="84" y="106" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="84" y="91" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="136" y="106" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="136" y="91" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="136" y="76" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="188" y="106" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="188" y="91" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="188" y="76" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="188" y="61" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="240" y="106" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="240" y="91" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="240" y="76" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="240" y="61" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="240" y="46" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="292" y="106" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="292" y="91" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="292" y="76" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="292" y="61" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="292" y="46" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="292" y="31" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="344" y="106" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="344" y="91" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="344" y="76" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="344" y="61" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="344" y="46" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-b" x="344" y="31" width="44" height="12" rx="2.5"/>
      <rect className="vt-dg-bp" x="344" y="16" width="44" height="12" rx="2.5"/></svg>
  ),
} as const;

export function AdimCizim({ no }: { no: 1 | 2 | 3 | 4 }) {
  return CIZIMLER[no];
}
