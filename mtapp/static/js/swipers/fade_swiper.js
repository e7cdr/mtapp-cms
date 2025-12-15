document.addEventListener('DOMContentLoaded', () => {
    const fadeContainer = document.querySelector('.fade-swiper-container');
    if (!fadeContainer) return;

    const totalSlides = fadeContainer.querySelectorAll('.swiper-slide').length;

    // Store YouTube players by realIndex
    const players = {};

    // Track if user has interacted (click/tap/key) — unlocks sound
    let userHasInteracted = false;
    document.addEventListener('click', () => { userHasInteracted = true; }, { once: true });
    document.addEventListener('touchstart', () => { userHasInteracted = true; }, { once: true });
    document.addEventListener('keydown', () => { userHasInteracted = true; }, { once: true });

    function loadAndPlayYouTubeVideo(container) {
        const videoId = container.dataset.videoId;
        const player = new YT.Player(container, {
            width: '100%',
            height: '100%',
            videoId: videoId,
            playerVars: {
                autoplay: 1,
                mute: 1,                  // Start muted → guaranteed autoplay everywhere
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
                    iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
                    iframe.setAttribute('loading', 'lazy');

                    e.target.playVideo();

                    // Unmute immediately if user already interacted
                    if (userHasInteracted) {
                        e.target.unMute();
                        e.target.setVolume(100); // Adjust volume as needed (0-100)
                    }
                },
                onStateChange: (e) => {
                    // Unmute on any state change if user has now interacted
                    if (userHasInteracted && e.data !== YT.PlayerState.ENDED) {
                        e.target.unMute();
                        e.target.setVolume(100);
                    }
                }
            }
        });
        return player;
    }

    const fadeSwiper = new Swiper(fadeContainer, {
        slidesPerView: 1,
        spaceBetween: 0,
        loop: totalSlides > 2,
        pagination: { el: '.swiper-pagination' },
        effect: 'fade',
        fadeEffect: { crossFade: true },
        speed: 2000,
        lazy: true,
        keyboard: true,
        grabCursor: true,
        allowTouchMove: true,
        on: {
            init: function () {
                const firstSlide = this.slides[this.activeIndex];
                const youtubeContainer = firstSlide.querySelector('.youtube-lazy');

                if (youtubeContainer) {
                    // Small delay for first YouTube slide to avoid API race
                    setTimeout(() => handleActiveSlide.call(this), 300);
                } else {
                    handleActiveSlide.call(this);
                }
            },
            slideChangeTransitionEnd: function () {
                handleActiveSlide.call(this);
            }
        }
    });

    function handleActiveSlide() {
        const activeRealIndex = this.realIndex;
        const activeSlide = this.slides[this.activeIndex];
        const youtubeContainer = activeSlide.querySelector('.youtube-lazy');

        // Pause & clean up previous video (if any)
        if (this.previousIndex !== undefined && this.previousIndex !== this.activeIndex) {
            const prevPlayer = players[this.previousRealIndex || activeRealIndex];
            if (prevPlayer) {
                prevPlayer.pauseVideo();
                if (prevPlayer._onEnded) {
                    prevPlayer.removeEventListener('onStateChange', prevPlayer._onEnded);
                    delete prevPlayer._onEnded;
                }
            }
        }

        if (youtubeContainer) {
            // YouTube slide
            let player = players[activeRealIndex];

            if (!player) {
                player = players[activeRealIndex] = loadAndPlayYouTubeVideo(youtubeContainer);
            } else {
                player.playVideo();

                // Unmute if user has interacted
                if (userHasInteracted) {
                    player.unMute();
                    player.setVolume(100);
                }
            }

            // Auto-advance only when video truly ends
            const onVideoEnded = (event) => {
                if (event.data === YT.PlayerState.ENDED) {
                    fadeSwiper.slideNext();
                }
            };

            if (!player._onEnded) {
                player._onEnded = onVideoEnded;
                player.addEventListener('onStateChange', onVideoEnded);
            }

        } else {
            // Image slide → auto-advance after delay
            setTimeout(() => {
                if (fadeSwiper.realIndex === activeRealIndex) {
                    fadeSwiper.slideNext();
                }
            }, 6000); // Adjust image display time here
        }
    }

    // Load YouTube Iframe API (only once)
    if (!window.YT) {
        const tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        const firstScript = document.getElementsByTagName('script')[0];
        firstScript.parentNode.insertBefore(tag, firstScript);
    }

    // === GSAP TITLE ANIMATION (unchanged) ===
    const titleEl = document.querySelector('.fade-title h1');
    const section = document.querySelector('.fade-swiper-section');

    if (titleEl && section) {
        document.fonts.ready.then(() => {
            gsap.registerPlugin(ScrollTrigger, SplitText);

            gsap.context(() => {
                const split = new SplitText(titleEl, { type: "chars" });

                const tl = gsap.timeline({
                    scrollTrigger: {
                        trigger: section,
                        start: "top 80%",
                        toggleActions: "play none none reverse"
                    }
                });

                tl.fromTo(fadeContainer,
                    { opacity: 0, y: 60 },
                    { opacity: 1, y: 0, duration: 1.4, ease: "power3.out" }
                );

                tl.to(split.chars, {
                    color: "#ffe66cff",
                    x: -3,
                    scale: 1.01,
                    duration: 0.9,
                    stagger: { from: "random", each: 0.04 },
                    repeat: -1,
                    yoyo: true,
                    repeatDelay: 3,
                    ease: "sine.inOut"
                }, "-=0.8");

            }, section);
        });
    }
});