/** G4-C1 test yardımcısı: Node tür-sıyırma ile kaynak modülü yüklerken uzantısız `../../lib/bicim` gibi içe aktarmalara `.ts` ekler (Vite çözer, Node çözmez). */
export async function resolve(spec, ctx, next) {
  try { return await next(spec, ctx); }
  catch (e) {
    if (e && e.code === "ERR_MODULE_NOT_FOUND" && (spec.startsWith("./") || spec.startsWith("../")) && !/\.[a-z]+$/i.test(spec)) return next(spec + ".ts", ctx);
    throw e;
  }
}
