document.addEventListener("DOMContentLoaded", () => {

    gsap.registerPlugin(ScrollTrigger, SplitText);
    let tl = gsap.timeline({
        scrollTrigger: ".basic-cta-container",
        scrub: 1,
        start: "top top",
    });
    tl.fromTo('.cta-section', {backgroundColor: "red", x: -200}, { x: 0, opacity: 1, duration: 1, ease: "power1.inOut", backgroundColor: "#282828"},
    ).fromTo('.action-button', { y: "random(-500, 900)", opacity: 0 }, { y: 0, opacity: 1, duration: 0.2, ease: "power1.inOut", },
    ).fromTo('.action-button-2', { x: "random(-800, 400)", opacity: 0 }, { x: 0, opacity: 1, duration: 0.1, ease: "power1.inOut", }
    ).fromTo('.top-text-side', { x: "random(-900, 500)", opacity: 0 }, { x: 0, opacity: 1, duration: 0.3, ease: "power1.inOut", }
    ).fromTo('.cta-image-container', { x: "random(-100, 200)", scale: 0, opacity: 0 }, { x: 0, opacity: 1, scale: 1, duration: 0.6 }
    ).to('.cta-section', { scale: 1.01, repeat: -1, yoyo: true, duration: 2, ease: "power1.inOut"});
    document.fonts.ready.then(() => {
        
    SplitText.create(".list-container li", 
        {type: "words",
        onSplit(self) {
            tl.from(self.words, {
                autoAlpha: 0,
                scale: 5,
                x: "random(-220, 600)",
                y: "random(-420, 100)",
                stagger: 0.05,
                duration: 0.6,
                ease: "power1.inOut",
            }, 0.7
            ).to(self.words, {color: "rgb(255, 192, 192)", y: -5, stagger: 0.11, repeat: -1, yoyo: true,
                onComplete: () => self.revert()
            });
        },
        
        });
        SplitText.create([".top-text-side", ".caption-zoom"], 
        {type: "words, chars",
        onSplit(self) {
            tl.from(self.words, {
                autoAlpha: 0,
                scale: 5,
                x: "random(-220, 600)",
                y: "random(-420, 100)",
                stagger: 0.05,
                duration: 0.6,
                ease: "power1.inOut",
            }, 0.5
            ).to(self.chars, {x: -4, stagger: 0.04, repeat: -1, yoyo: true,
                onComplete: () => self.revert()
            });
        },
        
        });
        // SplitText.create(".caption-zoom", 
        // {type: "chars",
        // onSplit(self) {
        //     tl.from(self.chars, {
        //         autoAlpha: 0,
        //         scale: 5,
        //         x: "random(-220, 600)",
        //         y: "random(-420, 100)",
        //         stagger: 0.05,
        //         duration: 0.6,
        //         ease: "power1.inOut",
        //     }, 0.9
        //     ).to(self.chars, {color: "rgba(0, 0, 0, 1)", scale: 1.15, textShadow: "0 0 0.2rem white", y: -5, stagger: 0.51, delay: 1, repeatDelay: 2, repeat: -1, yoyo: true,
        //         onComplete: () => self.revert()
        //     });
        // },
        
        // });
    });

    })
