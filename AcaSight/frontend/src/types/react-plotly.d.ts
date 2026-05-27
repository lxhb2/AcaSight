declare module 'react-plotly.js' {
  import { Component } from 'react';
  const Plot: any;
  export default Plot;
}

declare module 'react-plotly.js/factory' {
  const createPlotlyComponent: (Plotly: any) => any;
  export default createPlotlyComponent;
}

declare module 'plotly.js-dist-min' {
  const Plotly: any;
  export default Plotly;
  export const toImage: (div: any, opts: any) => Promise<string>;
}