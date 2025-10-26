  // Reusable function to initialize tab switching
  function initTabs(containerSelector, paneSelector) {
   const tabLinks = document.querySelectorAll(`${containerSelector} .nav-link`);
   const allTabPanes = document.querySelectorAll(paneSelector);

   tabLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
     event.preventDefault();

     const targetId = link.getAttribute('href');
     const targetTab = document.querySelector(targetId);

     // Reset all links
     tabLinks.forEach((otherLink) => otherLink.classList.remove('active'));

     // Hide all panes
     allTabPanes.forEach((pane) => {
      pane.classList.add('hidden');
      pane.classList.remove('show', 'active');
     });

     // Activate clicked link
     link.classList.add('active');

     // Show target pane
     if (targetTab) {
      targetTab.classList.add('show', 'active');
      targetTab.classList.remove('hidden');
     }

     console.log('Switched to tab: ' + targetId);
    });
   });
  }

  // Wait for DOM ready
  document.addEventListener('DOMContentLoaded', () => {
   // Initialize tour tabs
   initTabs('#tourTabs', '.tab-pane');

   // Initialize itinerary tabs
   initTabs('#itinerary-days', '#itinerary div');
  });