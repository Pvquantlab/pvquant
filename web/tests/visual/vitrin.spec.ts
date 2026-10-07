/** Vitrin görsel baseline'ları + deterministik değişmezler (Mühür D, v2.398).
 *  Baseline azdır ve kasıtlıdır (rapor 07): hero, panel kesiti, /yontem başı.
 *  Bilinçli tasarım değişiminde: npm run gorsel -- --update-snapshots → diff
 *  GÖZLE onaylanır → commit mesajına «görsel baseline güncellendi: <sebep>». */
import { test, expect, type Page } from "@playwright/test";
import { dondur, fontlariBekle } from "./dondur";

async function ac(page: Page, yol: string) {
  await dondur(page);
  await page.goto(yol, { waitUntil: "networkidle" });
  await fontlariBekle(page);
  // scroll-reveal: ekrana giren bölümler açılır; baseline hep «açılmış» hâli çeker
  await page.evaluate(() => {
    document.querySelectorAll("[data-canlan]").forEach((e) => {
      e.classList.remove("is-bekliyor"); e.classList.add("is-acildi");
    });
  });
  await page.waitForTimeout(250);
}

test("vitrin hero", async ({ page }) => {
  await ac(page, "/");
  await expect(page).toHaveScreenshot("vitrin-hero.png");
});

test("vitrin TL vakası (#para)", async ({ page }) => {
  // v2.416: «panel kesiti» yerini Ö4 vakasına bıraktı; baseline adı korunur
  await ac(page, "/");
  await page.locator("#para").scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  await expect(page.locator("#para")).toHaveScreenshot("vitrin-kesit.png");
});

test("yöntem sayfası başı", async ({ page }) => {
  await ac(page, "/yontem");
  await expect(page).toHaveScreenshot("yontem-bas.png");
});

/* ── Değişmezler: görüntüsüz, flake'siz — CI'ın bel kemiği adayları (rapor 07) ── */

for (const yol of ["/", "/yontem"]) {
  test(`değişmezler ${yol}`, async ({ page }) => {
    await ac(page, yol);
    const olcum = await page.evaluate(() => {
      const de = document.documentElement;
      const idler = [...document.querySelectorAll("[id]")].map((e) => e.id);
      let onceki = 0; const atlayan: string[] = [];
      for (const h of document.querySelectorAll("h1,h2,h3,h4,h5,h6")) {
        const sev = +h.tagName[1];
        if (onceki && sev > onceki + 1) atlayan.push(`h${onceki}→h${sev}`);
        onceki = sev;
      }
      const altsiz = [...document.querySelectorAll("img")].filter((i) => !i.hasAttribute("alt")).length;
      const isimsiz = [...document.querySelectorAll("button, a[href]")].filter((e) =>
        !((e.getAttribute("aria-label") || e.textContent || "").trim())).length;
      return {
        tasma: de.scrollWidth - de.clientWidth,
        ciftId: idler.length - new Set(idler).size,
        atlayan, altsiz, isimsiz,
      };
    });
    expect.soft(olcum.tasma, "yatay taşma").toBe(0);
    expect.soft(olcum.ciftId, "çift id").toBe(0);
    expect.soft(olcum.atlayan, "atlanan heading seviyesi").toEqual([]);
    expect.soft(olcum.altsiz, "alt'sız img").toBe(0);
    expect.soft(olcum.isimsiz, "isimsiz etkileşimli eleman").toBe(0);
  });
}
