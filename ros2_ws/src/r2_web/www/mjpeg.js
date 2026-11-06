// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// An MJPEG picture from web_video_server in an <img>. Asked for before the camera publishes
// (just after a restart), the server closes it and the <img> stays empty for good: so ask
// again every few seconds until the first picture arrives.
export function showStream(img, url, everyMs = 3000) {
  img.dataset.stream = url;
  img.src = url;
  let tries = 0;
  const check = () => {
    if (!img.isConnected || img.dataset.stream !== url || img.naturalWidth > 0) return;
    img.src = `${url}&retry=${++tries}`;
    setTimeout(check, everyMs);
  };
  setTimeout(check, everyMs);
}

// Close the MJPEG connection (and stop asking again)
export function stopStream(img) {
  delete img.dataset.stream;
  img.src = '';
}
