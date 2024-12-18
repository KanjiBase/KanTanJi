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

// Append the script to the <head> or <body>
parent.appendChild(tailwindScript);

const targetPage = currentScript.dataset.target;
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


