import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { VitrinKabugu } from "./VitrinKabugu";

/** Derleme betiği (vite.config «pvq-vitrin-kabugu») bu işlevi çağırır; istemci paketine girmez. */
export function kabukHtml(): string {
  return renderToStaticMarkup(createElement(VitrinKabugu));
}
