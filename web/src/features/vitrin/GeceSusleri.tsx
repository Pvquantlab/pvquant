/** Gece bandı süsleri — V1: sağ üstte üç güneş-yükseklik yayının çizgi hali + seyrek yıldız alanı
 *  (kaynak: vitrin-gorsel-kesif/varyant-1.html). Salt süs: aria-hidden, pointer-events yok; ≤1080 px'te
 *  CSS gizler. backdrop-filter KULLANILMAZ (v2.383 hayalet blok dersi) — yalnız çizgi ve nokta. */
export function GeceSusleri() {
  return (
    <>
      <svg className="vt-yildiz" viewBox="0 0 1440 360" preserveAspectRatio="xMidYMin slice" aria-hidden="true" focusable="false"><circle cx="466" cy="50" r="0.8" fill="#fff" fillOpacity="0.18"/>
      <circle cx="527" cy="19" r="0.8" fill="#fff" fillOpacity="0.18"/>
      <circle cx="624" cy="23" r="1.6" fill="#fff" fillOpacity="0.18"/>
      <circle cx="1191" cy="41" r="0.8" fill="#fff" fillOpacity="0.55"/>
      <circle cx="71" cy="73" r="1.0" fill="#fff" fillOpacity="0.40"/>
      <circle cx="604" cy="178" r="1.0" fill="#fff" fillOpacity="0.18"/>
      <circle cx="838" cy="211" r="0.8" fill="#fff" fillOpacity="0.18"/>
      <circle cx="891" cy="164" r="1.2" fill="#fff" fillOpacity="0.55"/>
      <circle cx="843" cy="150" r="1.0" fill="#fff" fillOpacity="0.28"/>
      <circle cx="118" cy="99" r="1.2" fill="#fff" fillOpacity="0.55"/>
      <circle cx="704" cy="13" r="1.2" fill="#fff" fillOpacity="0.40"/>
      <circle cx="1001" cy="196" r="1.6" fill="#fff" fillOpacity="0.18"/>
      <circle cx="1210" cy="312" r="0.8" fill="#fff" fillOpacity="0.18"/>
      <circle cx="1053" cy="102" r="1.6" fill="#fff" fillOpacity="0.40"/>
      <circle cx="1355" cy="117" r="1.6" fill="#fff" fillOpacity="0.18"/>
      <circle cx="314" cy="95" r="1.6" fill="#fff" fillOpacity="0.55"/>
      <circle cx="1320" cy="164" r="1.6" fill="#fff" fillOpacity="0.40"/>
      <circle cx="1272" cy="270" r="1.2" fill="#fff" fillOpacity="0.55"/>
      <circle cx="1421" cy="225" r="1.0" fill="#fff" fillOpacity="0.28"/>
      <circle cx="119" cy="50" r="0.8" fill="#fff" fillOpacity="0.55"/>
      <circle cx="1197" cy="60" r="1.0" fill="#fff" fillOpacity="0.55"/>
      <circle cx="181" cy="284" r="0.8" fill="#fff" fillOpacity="0.55"/>
      <circle cx="1295" cy="257" r="1.6" fill="#fff" fillOpacity="0.55"/>
      <circle cx="575" cy="34" r="0.8" fill="#fff" fillOpacity="0.28"/>
      <circle cx="97" cy="69" r="1.2" fill="#fff" fillOpacity="0.18"/>
      <circle cx="147" cy="187" r="1.2" fill="#fff" fillOpacity="0.18"/>
      <circle cx="101" cy="69" r="1.2" fill="#fff" fillOpacity="0.40"/>
      <circle cx="867" cy="156" r="1.6" fill="#fff" fillOpacity="0.55"/>
      <circle cx="692" cy="103" r="1.2" fill="#fff" fillOpacity="0.40"/>
      <circle cx="689" cy="228" r="1.0" fill="#fff" fillOpacity="0.40"/>
      <circle cx="211" cy="179" r="1.2" fill="#fff" fillOpacity="0.18"/>
      <circle cx="1003" cy="86" r="1.0" fill="#fff" fillOpacity="0.40"/>
      <circle cx="1112" cy="176" r="1.2" fill="#fff" fillOpacity="0.28"/>
      <circle cx="883" cy="260" r="1.0" fill="#fff" fillOpacity="0.28"/>
      <circle cx="745" cy="117" r="0.8" fill="#fff" fillOpacity="0.40"/>
      <circle cx="680" cy="64" r="1.2" fill="#fff" fillOpacity="0.55"/>
      <circle cx="1403" cy="27" r="1.6" fill="#fff" fillOpacity="0.28"/>
      <circle cx="486" cy="159" r="0.8" fill="#fff" fillOpacity="0.55"/>
      <circle cx="1309" cy="114" r="0.8" fill="#fff" fillOpacity="0.55"/>
      <circle cx="1127" cy="248" r="1.0" fill="#fff" fillOpacity="0.55"/></svg>
      <svg className="vt-gece-yay" viewBox="0 0 640 268" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false"><defs><linearGradient id="vt-gy" gradientUnits="userSpaceOnUse" x1="120" y1="0" x2="540" y2="0"><stop offset="0" stopColor="#fff" stopOpacity="0"/><stop offset=".25" stopColor="#fff" stopOpacity=".34"/><stop offset=".75" stopColor="#fff" stopOpacity=".34"/><stop offset="1" stopColor="#fff" stopOpacity="0"/></linearGradient></defs>
      <path d="M40 266H620" stroke="#fff" strokeOpacity=".18" strokeWidth="1"/>
      <path d="M167.9,262.3 C170.9,259.9 179.9,252.6 185.9,247.9 C191.9,243.1 197.9,238.3 203.9,233.8 C209.9,229.3 215.9,224.9 221.9,220.8 C227.9,216.6 233.9,212.7 239.9,209.0 C245.9,205.4 251.9,201.9 257.9,198.8 C263.9,195.7 269.9,192.8 275.9,190.4 C281.9,187.9 287.9,185.7 293.9,184.0 C299.9,182.2 305.9,180.8 311.9,179.9 C317.9,178.9 323.9,178.3 329.9,178.1 C335.9,177.9 341.9,178.2 347.9,178.9 C353.9,179.5 359.9,180.6 365.9,182.0 C371.9,183.5 377.9,185.4 383.9,187.5 C389.9,189.7 395.9,192.3 401.9,195.2 C407.9,198.0 413.9,201.3 419.9,204.7 C425.9,208.2 431.9,211.9 437.9,215.9 C443.9,219.8 449.9,224.1 455.9,228.5 C461.9,232.8 467.9,237.5 473.9,242.1 C479.9,246.8 486.9,252.6 491.9,256.6 C496.9,260.5 501.9,264.3 503.9,265.9" fill="none" stroke="url(#vt-gy)" strokeWidth="1.2"/>
      <path d="M114.0,262.5 C117.0,259.6 126.0,251.0 132.0,245.1 C138.0,239.2 144.0,233.1 150.0,227.2 C156.0,221.3 162.0,215.4 168.0,209.6 C174.0,203.7 180.0,197.9 186.0,192.3 C192.0,186.6 198.0,181.0 204.0,175.6 C210.0,170.2 216.0,164.9 222.0,159.8 C228.0,154.7 234.0,149.7 240.0,145.1 C246.0,140.5 252.0,136.0 258.0,132.0 C264.0,128.0 270.0,124.3 276.0,121.1 C282.0,117.8 288.0,115.0 294.0,112.8 C300.0,110.5 306.0,108.8 312.0,107.7 C318.0,106.6 324.0,106.1 330.0,106.3 C336.0,106.5 342.0,107.4 348.0,108.8 C354.0,110.2 360.0,112.3 366.0,114.8 C372.0,117.4 378.0,120.5 384.0,124.0 C390.0,127.4 396.0,131.4 402.0,135.6 C408.0,139.8 414.0,144.4 420.0,149.2 C426.0,154.0 432.0,159.1 438.0,164.2 C444.0,169.4 450.0,174.8 456.0,180.3 C462.0,185.8 468.0,191.5 474.0,197.2 C480.0,202.9 486.0,208.7 492.0,214.6 C498.0,220.4 504.0,226.4 510.0,232.3 C516.0,238.2 523.0,245.2 528.0,250.1 C533.0,255.0 538.0,259.7 540.0,261.6" fill="none" stroke="url(#vt-gy)" strokeWidth="1.2"/>
      <path d="M66.1,264.8 C69.1,262.3 78.1,255.0 84.1,249.8 C90.1,244.6 96.1,238.9 102.1,233.4 C108.1,227.8 114.1,222.1 120.1,216.3 C126.1,210.6 132.1,204.7 138.1,198.9 C144.1,193.0 150.1,187.1 156.1,181.1 C162.1,175.1 168.1,169.1 174.1,163.1 C180.1,157.0 186.1,151.0 192.1,145.0 C198.1,138.9 204.1,132.8 210.1,126.8 C216.1,120.8 222.1,114.7 228.1,108.8 C234.1,102.8 240.1,96.8 246.1,91.0 C252.1,85.2 258.1,79.5 264.1,74.0 C270.1,68.5 276.1,63.0 282.1,58.1 C288.1,53.2 294.1,48.4 300.1,44.7 C306.1,41.0 312.1,37.5 318.1,35.8 C324.1,34.1 330.1,33.6 336.1,34.5 C342.1,35.4 348.1,38.0 354.1,41.2 C360.1,44.4 366.1,48.9 372.1,53.5 C378.1,58.1 384.1,63.4 390.1,68.7 C396.1,74.1 402.1,79.8 408.1,85.5 C414.1,91.2 420.1,97.1 426.1,103.0 C432.1,109.0 438.1,115.0 444.1,121.0 C450.1,127.0 456.1,133.1 462.1,139.1 C468.1,145.2 474.1,151.3 480.1,157.3 C486.1,163.3 492.1,169.4 498.1,175.3 C504.1,181.3 510.1,187.3 516.1,193.2 C522.1,199.1 528.1,205.0 534.1,210.8 C540.1,216.6 546.1,222.4 552.1,228.0 C558.1,233.6 564.1,239.2 570.1,244.6 C576.1,250.0 584.1,256.9 588.1,260.3 C592.1,263.7 593.1,264.2 594.1,265.0" fill="none" stroke="url(#vt-gy)" strokeWidth="1.6"/></svg>
    </>
  );
}
