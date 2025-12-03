document.addEventListener('DOMContentLoaded', () => {
    let tl = gsap.timeline();
    
    tl.from(".navbar", {
        y: -400,
    }).fromTo(".navbar-logo", { opacity: 0, scale: 4, rotate: 30, duration: 1 }, {
        opacity: 1,
        duration: 1,
        scale: 1,
        rotate: 0,
    }).fromTo(".navbar-menu li", { opacity: 0, scale: 4 }, {        
        opacity: 1,
        duration: 1,
        scale: 1,
        stagger: {
            amount: 1,
        }
    }).fromTo("#languageToggle", { x: -200, y: 100, opacity: 0 }, {
        x: 0,
        y: 0,
        opacity: 1,
        
    });

})