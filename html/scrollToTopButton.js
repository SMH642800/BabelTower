// 回到頁面頂部的函式
// 当网页向下滑动 20px 出现"返回顶部" 按钮
window.onscroll = function() {scrollFunction()};
 
function scrollFunction() {
    var totalHeight = document.body.scrollHeight - window.innerHeight; // 網頁內容的總高度
    var currentScroll = document.documentElement.scrollTop || document.body.scrollTop;
    var goToTopBtn = document.getElementById("goToTopBtn");
    
    if (currentScroll > totalHeight * 0.2) {
        goToTopBtn.classList.add("show");
    } else {
        goToTopBtn.classList.remove("show");
    }
}
 
// 点击按钮，返回顶部
function topFunction() {
    scrollToTop()
}

// check user browser is used chromeium or not
function isChromium() {
    var isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
    var isChromium = window.chrome !== null;
  
    return isChrome && isChromium;
  }
  
// 返回页面顶部
function scrollToTop() {
    var currentScroll = document.documentElement.scrollTop || document.body.scrollTop;

    if (currentScroll > 0) {
        if (isChromium()) {
            var scrollStep = -currentScroll / (1000 / 15); // Adjust speed here for Chromium
            var scrollInterval = setInterval(function() {
              if (window.scrollY !== 0) {
                window.scrollBy(0, scrollStep);
              } else {
                clearInterval(scrollInterval);
              }
            }, 15);
        } else {
            window.requestAnimationFrame(scrollToTop);
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    }
  }