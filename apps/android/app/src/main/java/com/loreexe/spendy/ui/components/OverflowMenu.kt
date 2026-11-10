package com.loreexe.spendy.ui.components

import androidx.compose.foundation.layout.Box
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.painterResource
import com.loreexe.spendy.R

/**
 * Menu a tre puntini per le azioni distruttive o secondarie.
 * Evita che un tocco accidentale sul cestino elimini subito un elemento.
 */
@Composable
fun OverflowMenu(
    onDelete: (() -> Unit)? = null,
    onEdit: (() -> Unit)? = null,
    deleteLabel: String = "Elimina",
) {
    if (onDelete == null && onEdit == null) return
    var expanded by remember { mutableStateOf(false) }
    Box {
        IconButton(onClick = { expanded = true }) {
            Icon(painterResource(R.drawable.ic_lucide_more_vertical), contentDescription = "Altre azioni")
        }
        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            onEdit?.let { edit ->
                DropdownMenuItem(
                    text = { Text("Modifica") },
                    leadingIcon = {
                        Icon(painterResource(R.drawable.ic_lucide_pencil), contentDescription = null)
                    },
                    onClick = {
                        expanded = false
                        edit()
                    },
                )
            }
            onDelete?.let { delete ->
                DropdownMenuItem(
                    text = {
                        Text(
                            deleteLabel,
                            color = MaterialTheme.colorScheme.error,
                        )
                    },
                    leadingIcon = {
                        Icon(
                            painterResource(R.drawable.ic_lucide_trash_2),
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.error,
                        )
                    },
                    onClick = {
                        expanded = false
                        delete()
                    },
                )
            }
        }
    }
}
