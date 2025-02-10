const currentScript = document.currentScript;
const parent = currentScript.parentElement;

// Dynamically create a script tag for the Tailwind CDN
const tailwindScript = document.createElement('script');
tailwindScript.src = "https://cdn.tailwindcss.com";
tailwindScript.onload = () => {
  console.log("Tailwind CSS is loaded");
  // Optionally, configure Tailwind if needed
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          customColor: '#ff5733',
        },
      },
    },
  };
};
parent.appendChild(tailwindScript);

const embedCSS = document.createElement('link');
embedCSS.rel = 'stylesheet';
embedCSS.href = currentScript.src.slice(0, currentScript.src.length - 2) + "css";
document.head.appendChild(embedCSS);

let targetPage = currentScript.dataset.target.trim();
if (!targetPage.startsWith("http")) {
    const thisUrl = new URL(currentScript.src);
    const rootPath = thisUrl.pathname.substring(0, thisUrl.pathname.indexOf("misc/embed.js"));
    targetPage = `${thisUrl.protocol}//${thisUrl.hostname}${rootPath}static/${targetPage}`;
    if (!targetPage.endsWith(".html")) {
        targetPage = targetPage + ".html";
    }
}
const iframe = document.createElement("iframe");
iframe.src = targetPage;
iframe.style.width = '100%';
iframe.style.border = 'none';
iframe.style.minHeight = '700px';
iframe.id = 'ifrm';
parent.appendChild(iframe);

window.addEventListener("message", function(event) {
    const {
        iframeHeight
    } = event.data || {};
    if (iframeHeight) {
        const iframe = document.getElementById("ifrm");
        iframe.style.height = `${Number.parseInt(iframeHeight)}px`;
    }
});

if (currentScript.dataset.reinsert !== "false") {
    window.addEventListener('load', function () {

        // Re-attach existing elements to the nested container
        const otherNodesContainer = document.createElement("div");
        otherNodesContainer.classList.add("bonus-materials");
        otherNodesContainer.innerHTML = '<h3 class="bonus-title"> </h3>';
        const otherNodesContent = document.createElement("div");
        otherNodesContent.classList.add("bonus-content");
        const children = Array.from(parent.children);
        children.forEach(child => {
            // Avoid re-attaching scripts
            if (child.tagName !== "SCRIPT") {
                otherNodesContent.appendChild(child);
            }
        });
        otherNodesContainer.appendChild(otherNodesContent);
        parent.appendChild(otherNodesContainer);
    });
}


