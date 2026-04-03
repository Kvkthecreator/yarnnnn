import React from "react";
import type { Element } from "../types";
import { RenderElement } from "../elements";

const ELEMENT_STAGGER = 8;

type Props = {
  elements: Element[];
};

export const SplitLayout: React.FC<Props> = ({ elements }) => {
  const leftElements = elements.filter(
    (el) => "position" in el && el.position === "left"
  );
  const rightElements = elements.filter(
    (el) => "position" in el && el.position === "right"
  );
  // Elements without position go to left
  const unpositioned = elements.filter(
    (el) => !("position" in el) || !el.position || el.position === "center"
  );

  const left = [...unpositioned, ...leftElements];
  const right = rightElements;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        height: "100%",
        width: "100%",
        padding: "80px 100px",
        gap: 60,
      }}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          gap: 16,
        }}
      >
        {left.map((el, i) => (
          <RenderElement key={i} element={el} delay={i * ELEMENT_STAGGER} />
        ))}
      </div>
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "flex-end",
          gap: 16,
        }}
      >
        {right.map((el, i) => (
          <RenderElement
            key={i}
            element={el}
            delay={(left.length + i) * ELEMENT_STAGGER}
          />
        ))}
      </div>
    </div>
  );
};
