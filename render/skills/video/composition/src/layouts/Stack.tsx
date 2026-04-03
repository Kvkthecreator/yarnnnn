import React from "react";
import type { Element } from "../types";
import { RenderElement } from "../elements";

const ELEMENT_STAGGER = 8;

type Props = {
  elements: Element[];
};

export const StackLayout: React.FC<Props> = ({ elements }) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-start",
        height: "100%",
        width: "100%",
        gap: 20,
        padding: "80px 100px",
      }}
    >
      {elements.map((el, i) => (
        <RenderElement key={i} element={el} delay={i * ELEMENT_STAGGER} />
      ))}
    </div>
  );
};
