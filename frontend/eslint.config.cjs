module.exports = [
  {
    files: ["**/*.tsx"],
    languageOptions: {
      parser: require("@typescript-eslint/parser"),
    },
    plugins: {
      react: require("eslint-plugin-react"),
      "@typescript-eslint": require("@typescript-eslint/eslint-plugin"),
    },
    rules: {},
  },
];
