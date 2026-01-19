"use strict";
/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
exports.id = "vendor-chunks/remark-cjk-friendly-gfm-str_3fa91600760e3c8d4ac1e0416e14100e";
exports.ids = ["vendor-chunks/remark-cjk-friendly-gfm-str_3fa91600760e3c8d4ac1e0416e14100e"];
exports.modules = {

/***/ "(ssr)/./node_modules/.pnpm/remark-cjk-friendly-gfm-str_3fa91600760e3c8d4ac1e0416e14100e/node_modules/remark-cjk-friendly-gfm-strikethrough/dist/index.js":
/*!**********************************************************************************************************************************************************!*\
  !*** ./node_modules/.pnpm/remark-cjk-friendly-gfm-str_3fa91600760e3c8d4ac1e0416e14100e/node_modules/remark-cjk-friendly-gfm-strikethrough/dist/index.js ***!
  \**********************************************************************************************************************************************************/
/***/ ((__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (/* binding */ remarkGfmStrikethroughCjkFriendly)\n/* harmony export */ });\n/* harmony import */ var micromark_extension_cjk_friendly_gfm_strikethrough__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! micromark-extension-cjk-friendly-gfm-strikethrough */ \"(ssr)/./node_modules/.pnpm/micromark-extension-cjk-fri_388228cbac505e39802395acaf0b9ce9/node_modules/micromark-extension-cjk-friendly-gfm-strikethrough/dist/index.js\");\n// src/index.ts\n\nfunction remarkGfmStrikethroughCjkFriendly(options) {\n    const data = this.data();\n    const micromarkExtensions = // biome-ignore lint/suspicious/noAssignInExpressions: base plugin (remark-gfm) already does this\n    data.micromarkExtensions || (data.micromarkExtensions = []);\n    micromarkExtensions.push((0,micromark_extension_cjk_friendly_gfm_strikethrough__WEBPACK_IMPORTED_MODULE_0__.gfmStrikethroughCjkFriendly)(options));\n}\n\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHNzcikvLi9ub2RlX21vZHVsZXMvLnBucG0vcmVtYXJrLWNqay1mcmllbmRseS1nZm0tc3RyXzNmYTkxNjAwNzYwZTNjOGQ0YWMxZTA0MTZlMTQxMDBlL25vZGVfbW9kdWxlcy9yZW1hcmstY2prLWZyaWVuZGx5LWdmbS1zdHJpa2V0aHJvdWdoL2Rpc3QvaW5kZXguanMiLCJtYXBwaW5ncyI6Ijs7Ozs7QUFBQSxlQUFlO0FBRzZDO0FBQzVELFNBQVNDLGtDQUFrQ0MsT0FBTztJQUNoRCxNQUFNQyxPQUFPLElBQUksQ0FBQ0EsSUFBSTtJQUN0QixNQUFNQyxzQkFDSixpR0FBaUc7SUFDakdELEtBQUtDLG1CQUFtQixJQUFLRCxDQUFBQSxLQUFLQyxtQkFBbUIsR0FBRyxFQUFFO0lBRTVEQSxvQkFBb0JDLElBQUksQ0FBQ0wsK0dBQTJCQSxDQUFDRTtBQUN2RDtBQUdFIiwic291cmNlcyI6WyJ3ZWJwYWNrOi8vc2VudGluZWwtZnJvbnRlbmQvLi9ub2RlX21vZHVsZXMvLnBucG0vcmVtYXJrLWNqay1mcmllbmRseS1nZm0tc3RyXzNmYTkxNjAwNzYwZTNjOGQ0YWMxZTA0MTZlMTQxMDBlL25vZGVfbW9kdWxlcy9yZW1hcmstY2prLWZyaWVuZGx5LWdmbS1zdHJpa2V0aHJvdWdoL2Rpc3QvaW5kZXguanM/ZGZhMCJdLCJzb3VyY2VzQ29udGVudCI6WyIvLyBzcmMvaW5kZXgudHNcbmltcG9ydCB7XG4gIGdmbVN0cmlrZXRocm91Z2hDamtGcmllbmRseVxufSBmcm9tIFwibWljcm9tYXJrLWV4dGVuc2lvbi1jamstZnJpZW5kbHktZ2ZtLXN0cmlrZXRocm91Z2hcIjtcbmZ1bmN0aW9uIHJlbWFya0dmbVN0cmlrZXRocm91Z2hDamtGcmllbmRseShvcHRpb25zKSB7XG4gIGNvbnN0IGRhdGEgPSB0aGlzLmRhdGEoKTtcbiAgY29uc3QgbWljcm9tYXJrRXh0ZW5zaW9ucyA9IChcbiAgICAvLyBiaW9tZS1pZ25vcmUgbGludC9zdXNwaWNpb3VzL25vQXNzaWduSW5FeHByZXNzaW9uczogYmFzZSBwbHVnaW4gKHJlbWFyay1nZm0pIGFscmVhZHkgZG9lcyB0aGlzXG4gICAgZGF0YS5taWNyb21hcmtFeHRlbnNpb25zIHx8IChkYXRhLm1pY3JvbWFya0V4dGVuc2lvbnMgPSBbXSlcbiAgKTtcbiAgbWljcm9tYXJrRXh0ZW5zaW9ucy5wdXNoKGdmbVN0cmlrZXRocm91Z2hDamtGcmllbmRseShvcHRpb25zKSk7XG59XG5leHBvcnQge1xuICByZW1hcmtHZm1TdHJpa2V0aHJvdWdoQ2prRnJpZW5kbHkgYXMgZGVmYXVsdFxufTtcbiJdLCJuYW1lcyI6WyJnZm1TdHJpa2V0aHJvdWdoQ2prRnJpZW5kbHkiLCJyZW1hcmtHZm1TdHJpa2V0aHJvdWdoQ2prRnJpZW5kbHkiLCJvcHRpb25zIiwiZGF0YSIsIm1pY3JvbWFya0V4dGVuc2lvbnMiLCJwdXNoIiwiZGVmYXVsdCJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///(ssr)/./node_modules/.pnpm/remark-cjk-friendly-gfm-str_3fa91600760e3c8d4ac1e0416e14100e/node_modules/remark-cjk-friendly-gfm-strikethrough/dist/index.js\n");

/***/ })

};
;