/**
 * Call sortLineItems directly. canonicalCommitment rejects a tied triple
 * before the sort, so this path is the one that can observe the tie-break.
 */
import { sortLineItems } from "../src/canonicalize";

function item(title: string, amount: number) {
  return {
    line_id: "same",
    sku: "SKU-X",
    variant_id: "v",
    title,
    quantity: 1,
    unit_amount_minor: amount,
    total_amount_minor: amount,
  };
}

function titles(order: "ab" | "ba"): string[] {
  const items = order === "ab" ? [item("A", 1), item("B", 2)] : [item("B", 2), item("A", 1)];
  const out = sortLineItems({ line_items: items }) as { line_items: { title: string }[] };
  return out.line_items.map((row) => row.title);
}

const ab = titles("ab");
const ba = titles("ba");
console.log("ab", ab.join(","));
console.log("ba", ba.join(","));
if (ab.join(",") !== ba.join(",")) {
  console.error("FAIL  sortLineItems kept input order on a tied triple");
  process.exit(1);
}
if (ab.join(",") !== "A,B") {
  console.error("FAIL  expected A,B, got " + ab.join(","));
  process.exit(1);
}
console.log("PASS  sortLineItems tie-break is independent of input order");
