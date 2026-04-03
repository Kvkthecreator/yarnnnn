import React from "react";
import type { Element } from "../types";
import { Heading } from "./Heading";
import { TextElement } from "./TextElement";
import { Value } from "./Value";
import { Badge } from "./Badge";
import { List } from "./List";
import { Divider } from "./Divider";

type Props = {
  element: Element;
  delay: number;
};

export const RenderElement: React.FC<Props> = ({ element, delay }) => {
  switch (element.type) {
    case "heading":
      return (
        <Heading
          text={element.text}
          size={element.size}
          color={element.color}
          delay={delay}
        />
      );
    case "text":
      return (
        <TextElement
          text={element.text}
          size={element.size}
          color={element.color}
          delay={delay}
        />
      );
    case "value":
      return (
        <Value
          text={element.text}
          size={element.size}
          color={element.color}
          delay={delay}
        />
      );
    case "badge":
      return <Badge text={element.text} color={element.color} delay={delay} />;
    case "list":
      return <List items={element.items} delay={delay} />;
    case "divider":
      return <Divider delay={delay} />;
    case "spacer":
      return <div style={{ height: element.height || 40 }} />;
    default:
      return null;
  }
};
