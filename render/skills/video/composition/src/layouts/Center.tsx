import React from "react";
import type { Element } from "../types";
import { RenderElement } from "../elements";

const ELEMENT_STAGGER = 8; // frames between element entrances

type Props = {
  elements: Element[];
};

export const CenterLayout: React.FC<Props> = ({ elements }) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        width: "100%",
        gap: 16,
        textAlign: "center",
        padding: "60px 80px",
      }}
    >
      {elements.map((el, i) => (
        <RenderElement key={i} element={el} delay={i * ELEMENT_STAGGER} />
      ))}
    </div>
  );
};
