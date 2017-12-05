'use strict';
/*
 * Author: Wender Lima
 * Github: https://github.com/wender/angular-slide-wrapper
 * */
function SlideWrapperDirective($compile, $interval) {
  return {
    restrict: 'E',
    scope: true,
    link: function (scope, el, attr) {
      // Top level variables definition
      var html = '';
      var uls = el[0].querySelectorAll('ul');
      var items = uls[0].querySelectorAll('li');
      var cssBullets = 'bullets';
      var auto = attr.auto === 'false' ? false : true;
      var bullet = attr.bullet === 'false' ? false : true;
      var arrows = attr.arrows === 'false' ? false : true;
      var hover = false;
      var interval = null;
      var touchPosition = {
        initialX: null,
        currentX: null,
        initialMargin: null,
        diff: null
      };

      // scope definitions
      scope.current = 0;
      scope.total = items.length || 0;
      scope.width = el[0].clientWidth || 0;
      scope.bulletWidth = null;
      scope.showArrows = true;


      // actions
      function setMargin(n) {
        uls[0].style.marginLeft = (n ? '-' + (scope.width * n) : n) + 'px';
      };

      scope.goTo = function (i, apply) {
        if (scope.current !== i) {
          scope.current = i;
          if (apply) {
            scope.$apply();
          }
        } else {
          setMargin(i);
        }
      };
      scope.prev = function (apply) {
        var apply = apply || false;
        scope.goTo(scope.current > 0 ? scope.current - 1 : (apply ? scope.current : scope.total - 1), apply);
      };
      scope.next = function (apply) {
        var apply = apply || false;
        scope.goTo(scope.current < (scope.total - 1) ? scope.current + 1 : (apply ? scope.current : 0), apply);
      };
      scope.$watch('current', function (n) {
        setMargin(n);
      });

      // Auto slide
      function startInterval() {
        interval = $interval(function () {
          if (!hover) {
            scope.next();
          }
        }, 5000);
      }

      if (auto) {

        el[0].addEventListener('mouseenter', function () {
          hover = true;
        }, false);
        el[0].addEventListener('touchstart', function (e) {
          hover = true;
          angular.element(uls[0]).addClass('touch');
          touchPosition.initialX = e.changedTouches[0].pageX;
          touchPosition.initialMargin = parseInt(angular.element(uls[0]).css('margin-left').replace('px', ''));
          $interval.cancel(interval);
        }, false);
        el[0].addEventListener('mouseleave', function () {
          hover = false;
        }, false);
        el[0].addEventListener('touchend', function () {
          hover = false;
          angular.element(uls[0]).removeClass('touch');
          if (touchPosition.diff !== null) {
            if (touchPosition.diff > 0) {
              scope.prev(true);
            } else {
              scope.next(true);
            }
            scope.showArrows = false;
          }
          startInterval();
        }, false);
        startInterval();
      }

      // Touch events
      el[0].addEventListener('touchmove', function (e) {
        touchPosition.currentX = e.changedTouches[0].pageX;
        touchPosition.diff = parseInt(touchPosition.currentX - touchPosition.initialX);
        if(touchPosition.diff){
          e.preventDefault();
          var newMargin = touchPosition.initialMargin + touchPosition.diff;
          uls[0].style.marginLeft = newMargin + 'px';
        }
      }, true);


      // Resize
      window.addEventListener('resize', function () {
        reset();
      });


      // dom manipulation
      function reset() {
        uls[0].style.marginLeft = 0;
        scope.current = 0;
        el[0].style.opacity = 0;
        applyWidth(true);
        applyBulletWidth(true);
        scope.width = el[0].clientWidth || 0;
        setTimeout(function () {
          applyWidth();
          applyBulletWidth();
          el[0].style.opacity = 1;
        }, 500);
      }

      function applyWidth(clear) {
        var clear = clear || false;
        uls[0].style.width = clear ? 'auto' : (scope.width * items.length) + 'px';
        for (var a in items) {
          if (typeof items[a] === 'object') {
            items[a].style.width = clear ? 'auto' : scope.width + 'px';
          }
        }
      }

      angular.element(uls[0]).addClass('slide');
      applyWidth();

      if (arrows) {
        html += '<span class="arrow left" ng-click="prev()" ng-show="showArrows && current>0"><i class="fa fa-chevron-left"></i></span><span class="arrow right" ng-click="next()" ng-show="showArrows && current<(total-1)"><i class="fa fa-chevron-right"></i></span>';
      }

      if (bullet) {
        if (uls.length === 1) {
          html += '<ul class="' + cssBullets + '" ng-style="bulletWidth">';
          for (var a in items) {
            if (typeof items[a] === 'object') {
              html += '<li ng-class="{\'active\':current==' + a + '}" class="item_' + a + '" ng-click="goTo(' + a + ')"></li>';
            }
          }
        } else {
          cssBullets = 'custom';
          html += '<ul class="' + cssBullets + '" ng-style="bulletWidth">';
          var customBullets = uls[1].querySelectorAll('li');
          for (var a in items) {
            if (typeof items[a] === 'object') {
              html += '<li ng-class="{\'active\':current==' + a + '}" class="item_' + a + '" ng-click="goTo(' + a + ')">' + customBullets[a].innerHTML + '</li>';
            }
          }
        }
      }

      html += '</ul>';

      // remove custom bullet, will be replaced by the new one
      if (uls[1]) {
        angular.element(uls[1]).remove();
      }

      // compile html to angular's scope
      var linkFn = $compile(html);
      var content = linkFn(scope);
      el.append(content);

      // setting bullets width based on new elements
      function applyBulletWidth(clear) {
        var clear = clear || false;
        scope.bulletWidth = {
          'width': clear ? 'auto' : el[0].querySelectorAll('ul.' + cssBullets)[0].clientWidth + 'px',
          'margin-left': 'calc(50% - ' + (el[0].querySelectorAll('ul.' + cssBullets)[0].clientWidth / 2) + 'px)'
        };
      }

      applyBulletWidth();
    }
  };
}

angular.module('slideWrapper', [])
  .directive('slideWrapper', ['$compile', '$interval', SlideWrapperDirective]);
