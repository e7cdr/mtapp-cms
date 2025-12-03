document.addEventListener('DOMContentLoaded', function () {
    // Fix loop warning if not enough slides
    const totalSlides = document.querySelectorAll('.fade-swiper-container .swiper-slide').length;

    var fadeSwiper = new Swiper('.fade-swiper-container', {
        slidesPerView: 1,                         // Fade effect only works with 1 slide visible
        spaceBetween: 0,
        loop: totalSlides > 2,                    // Auto-disable loop if ≤2 items
        pagination: {
            el: '.swiper-pagination',
        },
        effect: 'fade',
        fadeEffect: {
            crossFade: true
        },
        autoplay: false,                          // We control timing manually
        speed: 2000,
        lazy: true,
        keyboard: true,
        grabCursor: true,
        allowTouchMove: true                      // Optional: allow swipe on mobile
    });

    const players = {};

    function loadAndPlayYouTubeVideo(container) {
        const videoId = container.dataset.videoId;
        const player = new YT.Player(container, {
            width: '100%',
            height: '100%',
            videoId: videoId,
            playerVars: {
                autoplay: 1,
                rel: 0,
                modestbranding: 1,
                playsinline: 1,
                fs: 1,
                enablejsapi: 1,
                origin: window.location.origin
            },
            events: {
                onReady: (e) => {
                    const iframe = e.target.getIframe();
                    iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; passive-touch');
                    iframe.setAttribute('loading', 'lazy');
                    e.target.playVideo();
                }
            }
        });
        return player;
    }

    // Main magic: runs on every slide change
    fadeSwiper.on('slideChange transitionEnd', function () {
        const prevIndex = this.previousRealIndex !== undefined ? this.previousRealIndex : this.realIndex;
        const activeIndex = this.realIndex;

        // Pause & clean previous video
        if (players[prevIndex]) {
            players[prevIndex].pauseVideo();
            if (players[prevIndex]._onEnded) {
                players[prevIndex].removeEventListener('onStateChange', players[prevIndex]._onEnded);
            }
        }

        const activeSlide = this.slides[this.activeIndex];
        const youtubeContainer = activeSlide.querySelector('.youtube-lazy');

        if (youtubeContainer) {
            // YouTube slide
            if (!players[activeIndex]) {
                players[activeIndex] = loadAndPlayYouTubeVideo(youtubeContainer);
            } else {
                players[activeIndex].playVideo();
            }

            // Auto-next when video ends
            const player = players[activeIndex];
            const onEnded = (event) => {
                if (event.data === YT.PlayerState.ENDED) {
                    fadeSwiper.slideNext();
                }
            };
            player._onEnded = onEnded;
            player.addEventListener('onStateChange', onEnded);

        } else {
            // Image slide → auto-advance after delay
            setTimeout(() => {
                if (fadeSwiper.realIndex === activeIndex) {
                    fadeSwiper.slideNext();
                }
            }, 6000); // 6 seconds for images
        }
    });

    // Start the show
    fadeSwiper.on('init', function () {
        setTimeout(() => this.emit('slideChange'), 400);
    });
    fadeSwiper.init();

    // Load YouTube API only once
    if (!window.YT) {
        const tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        const firstScript = document.getElementsByTagName('script')[0];
        firstScript.parentNode.insertBefore(tag, firstScript);
    }
});