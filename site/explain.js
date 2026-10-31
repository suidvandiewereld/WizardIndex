// The explainer pages (AI basics, Security, How it works): every question has its own link, and
// clicking it copies that address so the answer can be sent to whoever asked. Without a clipboard
// it is an ordinary link to the answer.
// One listener for the whole page, so links drawn later (the Tools page) work too.
document.addEventListener("click", e => {
  const a = e.target.closest("a.permalink");
  if (!a || !navigator.clipboard) return;
  const hash = a.getAttribute("href");
  e.preventDefault();
  history.replaceState(null, "", hash);
  navigator.clipboard.writeText(location.href).then(() => {
    a.textContent = "link copied";
    setTimeout(() => { a.textContent = "link"; }, 1500);
  }, () => { location.hash = hash; });
});

// "On this page" lives in the sidebar, which drops below everything on narrow screens (style.css,
// max-width 1160px). There it moves up under the page's introduction, so it still works as an index.
const toc = document.querySelector(".box.toc");
if (toc) {
  const home = toc.parentElement, after = toc.nextElementSibling;
  const intro = document.querySelector("#main > p");
  const narrow = matchMedia("(max-width: 1160px)");
  const place = () => narrow.matches ? intro.after(toc) : home.insertBefore(toc, after);
  narrow.addEventListener("change", place);
  place();
}
