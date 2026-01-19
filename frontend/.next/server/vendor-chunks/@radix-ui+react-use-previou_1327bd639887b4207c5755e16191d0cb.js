"use strict";
/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
exports.id = "vendor-chunks/@radix-ui+react-use-previou_1327bd639887b4207c5755e16191d0cb";
exports.ids = ["vendor-chunks/@radix-ui+react-use-previou_1327bd639887b4207c5755e16191d0cb"];
exports.modules = {

/***/ "(ssr)/./node_modules/.pnpm/@radix-ui+react-use-previou_1327bd639887b4207c5755e16191d0cb/node_modules/@radix-ui/react-use-previous/dist/index.mjs":
/*!**************************************************************************************************************************************************!*\
  !*** ./node_modules/.pnpm/@radix-ui+react-use-previou_1327bd639887b4207c5755e16191d0cb/node_modules/@radix-ui/react-use-previous/dist/index.mjs ***!
  \**************************************************************************************************************************************************/
/***/ ((__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   usePrevious: () => (/* binding */ usePrevious)\n/* harmony export */ });\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react */ \"(ssr)/./node_modules/.pnpm/next@14.1.0_@opentelemetry+_95d5a05ac7ec0d735f17a907e734f3d8/node_modules/next/dist/server/future/route-modules/app-page/vendored/ssr/react.js\");\n// packages/react/use-previous/src/use-previous.tsx\n\nfunction usePrevious(value) {\n    const ref = react__WEBPACK_IMPORTED_MODULE_0__.useRef({\n        value,\n        previous: value\n    });\n    return react__WEBPACK_IMPORTED_MODULE_0__.useMemo(()=>{\n        if (ref.current.value !== value) {\n            ref.current.previous = ref.current.value;\n            ref.current.value = value;\n        }\n        return ref.current.previous;\n    }, [\n        value\n    ]);\n}\n //# sourceMappingURL=index.mjs.map\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHNzcikvLi9ub2RlX21vZHVsZXMvLnBucG0vQHJhZGl4LXVpK3JlYWN0LXVzZS1wcmV2aW91XzEzMjdiZDYzOTg4N2I0MjA3YzU3NTVlMTYxOTFkMGNiL25vZGVfbW9kdWxlcy9AcmFkaXgtdWkvcmVhY3QtdXNlLXByZXZpb3VzL2Rpc3QvaW5kZXgubWpzIiwibWFwcGluZ3MiOiI7Ozs7O0FBQUEsbURBQW1EO0FBQ3BCO0FBQy9CLFNBQVNDLFlBQVlDLEtBQUs7SUFDeEIsTUFBTUMsTUFBTUgseUNBQVksQ0FBQztRQUFFRTtRQUFPRyxVQUFVSDtJQUFNO0lBQ2xELE9BQU9GLDBDQUFhLENBQUM7UUFDbkIsSUFBSUcsSUFBSUksT0FBTyxDQUFDTCxLQUFLLEtBQUtBLE9BQU87WUFDL0JDLElBQUlJLE9BQU8sQ0FBQ0YsUUFBUSxHQUFHRixJQUFJSSxPQUFPLENBQUNMLEtBQUs7WUFDeENDLElBQUlJLE9BQU8sQ0FBQ0wsS0FBSyxHQUFHQTtRQUN0QjtRQUNBLE9BQU9DLElBQUlJLE9BQU8sQ0FBQ0YsUUFBUTtJQUM3QixHQUFHO1FBQUNIO0tBQU07QUFDWjtBQUdFLENBQ0Ysa0NBQWtDIiwic291cmNlcyI6WyJ3ZWJwYWNrOi8vc2VudGluZWwtZnJvbnRlbmQvLi9ub2RlX21vZHVsZXMvLnBucG0vQHJhZGl4LXVpK3JlYWN0LXVzZS1wcmV2aW91XzEzMjdiZDYzOTg4N2I0MjA3YzU3NTVlMTYxOTFkMGNiL25vZGVfbW9kdWxlcy9AcmFkaXgtdWkvcmVhY3QtdXNlLXByZXZpb3VzL2Rpc3QvaW5kZXgubWpzPzlkNmEiXSwic291cmNlc0NvbnRlbnQiOlsiLy8gcGFja2FnZXMvcmVhY3QvdXNlLXByZXZpb3VzL3NyYy91c2UtcHJldmlvdXMudHN4XG5pbXBvcnQgKiBhcyBSZWFjdCBmcm9tIFwicmVhY3RcIjtcbmZ1bmN0aW9uIHVzZVByZXZpb3VzKHZhbHVlKSB7XG4gIGNvbnN0IHJlZiA9IFJlYWN0LnVzZVJlZih7IHZhbHVlLCBwcmV2aW91czogdmFsdWUgfSk7XG4gIHJldHVybiBSZWFjdC51c2VNZW1vKCgpID0+IHtcbiAgICBpZiAocmVmLmN1cnJlbnQudmFsdWUgIT09IHZhbHVlKSB7XG4gICAgICByZWYuY3VycmVudC5wcmV2aW91cyA9IHJlZi5jdXJyZW50LnZhbHVlO1xuICAgICAgcmVmLmN1cnJlbnQudmFsdWUgPSB2YWx1ZTtcbiAgICB9XG4gICAgcmV0dXJuIHJlZi5jdXJyZW50LnByZXZpb3VzO1xuICB9LCBbdmFsdWVdKTtcbn1cbmV4cG9ydCB7XG4gIHVzZVByZXZpb3VzXG59O1xuLy8jIHNvdXJjZU1hcHBpbmdVUkw9aW5kZXgubWpzLm1hcFxuIl0sIm5hbWVzIjpbIlJlYWN0IiwidXNlUHJldmlvdXMiLCJ2YWx1ZSIsInJlZiIsInVzZVJlZiIsInByZXZpb3VzIiwidXNlTWVtbyIsImN1cnJlbnQiXSwic291cmNlUm9vdCI6IiJ9\n//# sourceURL=webpack-internal:///(ssr)/./node_modules/.pnpm/@radix-ui+react-use-previou_1327bd639887b4207c5755e16191d0cb/node_modules/@radix-ui/react-use-previous/dist/index.mjs\n");

/***/ })

};
;