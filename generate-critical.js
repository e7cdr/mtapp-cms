// generate-critical.js
(async () => {
  const critical = await import('critical');

  critical.generate({
    inline: false,
    base: './',
    src: 'http://127.0.0.1:8000/en/',
    target: {
      css: 'static/css/critical.css',
    },
    width: 375,
    height: 667,
    penthouse: {
      timeout: 60000,
      renderWaitTime: 2000,
    },
    ignore: [/swiper/, /font-awesome/, /bootstrap-icons/],
  }).then(result => {
    console.log('Critical CSS generated! → static/css/critical.css');
    console.log(`Size: ${(result.css.length / 1024).toFixed(1)} KB`);
  }).catch(err => {
    console.error('Error:', err);
  });
})();