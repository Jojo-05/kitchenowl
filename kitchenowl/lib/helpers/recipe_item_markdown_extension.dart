import 'package:collection/collection.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:fraction/fraction.dart';
import 'package:kitchenowl/cubits/recipe_cubit.dart';
import 'package:kitchenowl/helpers/string_scaler.dart';
import 'package:kitchenowl/models/item.dart';
import 'package:kitchenowl/models/recipe.dart';
import 'package:kitchenowl/widgets/item_chip.dart';
import 'package:markdown/markdown.dart' as md;
import 'package:material_ui/material_ui.dart';

String cleanRecipeItemName(String name) {
  return name.toLowerCase().replaceAll(
      RegExp(r"""\n|\.|\(|\)|\\|\/|\?|\*|\+|,|!|%|$|#|@|^|;|:|"|=|~|{"""),
      "");
}

class RecipeItemMarkdownBuilder extends MarkdownElementBuilder {
  final List<RecipeItem> items;
  final Fraction? itemScaledFactor;

  RecipeItemMarkdownBuilder({required this.items, this.itemScaledFactor});

  @override
  Widget? visitElementAfterWithContext(
    BuildContext context,
    md.Element element,
    TextStyle? preferredStyle,
    TextStyle? parentStyle,
  ) {
    if ((parentStyle?.fontSize ?? 0) > 14) return null;

    final item = items
        .where((e) => cleanRecipeItemName(e.name) == element.textContent)
        .firstOrNull;
    if (item == null) {
      return Text(element.textContent, style: parentStyle);
    }

    String? overridenDescription = element.attributes["description"];
    if (overridenDescription != null && itemScaledFactor != null) {
      overridenDescription =
          StringScaler.scale(overridenDescription, itemScaledFactor!);
    }
    return RichText(
      text: TextSpan(children: [
        WidgetSpan(
          alignment: PlaceholderAlignment.middle,
          child: ItemChip(
            item: item,
            description: overridenDescription,
          ),
        ),
      ]),
    );
  }
}

class RecipeCubitItemMarkdownBuilder extends MarkdownElementBuilder {
  final RecipeCubit cubit;

  RecipeCubitItemMarkdownBuilder({required this.cubit});

  String cleanItemName(String name) => cleanRecipeItemName(name);

  @override
  Widget? visitElementAfterWithContext(
    BuildContext context,
    md.Element element,
    TextStyle? preferredStyle,
    TextStyle? parentStyle,
  ) {
    if ((parentStyle?.fontSize ?? 0) > 14) return null;

    return RichText(
      text: TextSpan(children: [
        WidgetSpan(
          alignment: PlaceholderAlignment.middle,
          child: BlocBuilder<RecipeCubit, RecipeState>(
            bloc: cubit,
            buildWhen: (previous, current) {
              final prevItem = previous.dynamicRecipe.items
                  .where((e) => cleanRecipeItemName(e.name) == element.textContent)
                  .firstOrNull;
              final currItem = current.dynamicRecipe.items
                  .where((e) => cleanRecipeItemName(e.name) == element.textContent)
                  .firstOrNull;
              return prevItem != currItem ||
                  previous.selectedYields != current.selectedYields;
            },
            builder: (context, state) {
              final item = state.dynamicRecipe.items
                  .where((e) => cleanRecipeItemName(e.name) == element.textContent)
                  .firstOrNull;

              if (item == null) {
                return Text(element.textContent, style: parentStyle);
              }

              String? overridenDescription = element.attributes["description"];
              if (overridenDescription != null &&
                  state.recipe.yields != 0 &&
                  state.selectedYields != null &&
                  state.recipe.yields != state.selectedYields) {
                overridenDescription = StringScaler.scale(overridenDescription,
                    Fraction(state.selectedYields!, state.recipe.yields));
              }

              return ItemChip(
                item: item,
                description: overridenDescription,
              );
            },
          ),
        ),
      ]),
    );
  }
}

class RecipeExplicitItemMarkdownSyntax extends md.InlineSyntax {
  final Recipe recipe;

  RecipeExplicitItemMarkdownSyntax(this.recipe)
      : super(
          _pattern,
          caseSensitive: false,
        );

  static const String _pattern =
      r"""@([^ \n\.\(\)\\\/\?\*\+,!%$#@^;:"=~{]+)({([^}]*)})?"""; // TODO: replace with \p{L} and unicode=true

  @override
  bool onMatch(md.InlineParser parser, Match match) {
    final name = cleanRecipeItemName(match[1]!.replaceAll("_", " ").trim());
    if (!recipe.items
        .map((e) => cleanRecipeItemName(e.name))
        .contains(name)) {
      parser.advanceBy(1);

      return false;
    }

    final node = md.Element.text('recipeItem', name);
    if (match.group(3) != null) {
      node.attributes["description"] = match.group(3)!;
    }
    parser.addNode(node);

    return true;
  }
}
