"use strict";
/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
exports.id = "vendor-chunks/remark-cjk-friendly@1.2.3_@_d27ae5b708100f0d0cecfd849d45027f";
exports.ids = ["vendor-chunks/remark-cjk-friendly@1.2.3_@_d27ae5b708100f0d0cecfd849d45027f"];
exports.modules = {

/***/ "(ssr)/./node_modules/.pnpm/remark-cjk-friendly@1.2.3_@_d27ae5b708100f0d0cecfd849d45027f/node_modules/remark-cjk-friendly/dist/index.js":
/*!****************************************************************************************************************************************!*\
  !*** ./node_modules/.pnpm/remark-cjk-friendly@1.2.3_@_d27ae5b708100f0d0cecfd849d45027f/node_modules/remark-cjk-friendly/dist/index.js ***!
  \****************************************************************************************************************************************/
/***/ ((__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (/* binding */ remarkCjkFriendly)\n/* harmony export */ });\n/* harmony import */ var micromark_extension_cjk_friendly__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! micromark-extension-cjk-friendly */ \"(ssr)/./node_modules/.pnpm/micromark-extension-cjk-fri_8e9af7defa581847d2b8c66351e69f5f/node_modules/micromark-extension-cjk-friendly/dist/index.js\");\n// src/index.ts\n\nfunction remarkCjkFriendly() {\n    const data = this.data();\n    const micromarkExtensions = // biome-ignore lint/suspicious/noAssignInExpressions: base plugin (remark-gfm) already does this\n    data.micromarkExtensions || (data.micromarkExtensions = []);\n    micromarkExtensions.push((0,micromark_extension_cjk_friendly__WEBPACK_IMPORTED_MODULE_0__.cjkFriendlyExtension)());\n}\n\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHNzcikvLi9ub2RlX21vZHVsZXMvLnBucG0vcmVtYXJrLWNqay1mcmllbmRseUAxLjIuM19AX2QyN2FlNWI3MDgxMDBmMGQwY2VjZmQ4NDlkNDUwMjdmL25vZGVfbW9kdWxlcy9yZW1hcmstY2prLWZyaWVuZGx5L2Rpc3QvaW5kZXguanMiLCJtYXBwaW5ncyI6Ijs7Ozs7QUFBQSxlQUFlO0FBQ3lEO0FBQ3hFLFNBQVNDO0lBQ1AsTUFBTUMsT0FBTyxJQUFJLENBQUNBLElBQUk7SUFDdEIsTUFBTUMsc0JBQ0osaUdBQWlHO0lBQ2pHRCxLQUFLQyxtQkFBbUIsSUFBS0QsQ0FBQUEsS0FBS0MsbUJBQW1CLEdBQUcsRUFBRTtJQUU1REEsb0JBQW9CQyxJQUFJLENBQUNKLHNGQUFvQkE7QUFDL0M7QUFHRSIsInNvdXJjZXMiOlsid2VicGFjazovL3NlbnRpbmVsLWZyb250ZW5kLy4vbm9kZV9tb2R1bGVzLy5wbnBtL3JlbWFyay1jamstZnJpZW5kbHlAMS4yLjNfQF9kMjdhZTViNzA4MTAwZjBkMGNlY2ZkODQ5ZDQ1MDI3Zi9ub2RlX21vZHVsZXMvcmVtYXJrLWNqay1mcmllbmRseS9kaXN0L2luZGV4LmpzPzNhMTgiXSwic291cmNlc0NvbnRlbnQiOlsiLy8gc3JjL2luZGV4LnRzXG5pbXBvcnQgeyBjamtGcmllbmRseUV4dGVuc2lvbiB9IGZyb20gXCJtaWNyb21hcmstZXh0ZW5zaW9uLWNqay1mcmllbmRseVwiO1xuZnVuY3Rpb24gcmVtYXJrQ2prRnJpZW5kbHkoKSB7XG4gIGNvbnN0IGRhdGEgPSB0aGlzLmRhdGEoKTtcbiAgY29uc3QgbWljcm9tYXJrRXh0ZW5zaW9ucyA9IChcbiAgICAvLyBiaW9tZS1pZ25vcmUgbGludC9zdXNwaWNpb3VzL25vQXNzaWduSW5FeHByZXNzaW9uczogYmFzZSBwbHVnaW4gKHJlbWFyay1nZm0pIGFscmVhZHkgZG9lcyB0aGlzXG4gICAgZGF0YS5taWNyb21hcmtFeHRlbnNpb25zIHx8IChkYXRhLm1pY3JvbWFya0V4dGVuc2lvbnMgPSBbXSlcbiAgKTtcbiAgbWljcm9tYXJrRXh0ZW5zaW9ucy5wdXNoKGNqa0ZyaWVuZGx5RXh0ZW5zaW9uKCkpO1xufVxuZXhwb3J0IHtcbiAgcmVtYXJrQ2prRnJpZW5kbHkgYXMgZGVmYXVsdFxufTtcbiJdLCJuYW1lcyI6WyJjamtGcmllbmRseUV4dGVuc2lvbiIsInJlbWFya0Nqa0ZyaWVuZGx5IiwiZGF0YSIsIm1pY3JvbWFya0V4dGVuc2lvbnMiLCJwdXNoIiwiZGVmYXVsdCJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///(ssr)/./node_modules/.pnpm/remark-cjk-friendly@1.2.3_@_d27ae5b708100f0d0cecfd849d45027f/node_modules/remark-cjk-friendly/dist/index.js\n");

/***/ })

};
;